"""Tests for the realtime layer (streaming, pipeline, replay, webapp).

No microphone and no whisper model: fake frames, fake engines, a synthetic WAV.

Checks:
    1. UtteranceSegmenter closes on silence, drops blips, flushes long speech.
    2. LocalAgreement commits a word only after two hypotheses agree.
    3. accurate mode: one decode per sentence, no draft events.
    4. realtime mode: draft events flow before the sentence closes.
    5. clear discards a decode that was already in flight.
    6. Engine settings reload in the background and swap atomically.
    7. Replay: list, upload (path sanitiser), decode with timing.
    8. UiServer serves the page, settings, devices, samples and replay.

Run:  python test_streaming.py
"""

from __future__ import annotations

import json
import queue
import sys
import tempfile
import threading
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.constants import BLOCK, SAMPLE_RATE
from backend.config.settings import Settings
from backend.main import create_app
from backend.models.dto import ReplayResult
from backend.services.engines import (available_engines, create_engine,
                                      register_engine)
from backend.services.engines.base import ASREngine
from backend.services.engines.zipformer_engine import MODEL_DIR
from backend.services.event_service import EventBus
from backend.services.replay_service import ReplayService
from backend.services.segmentation_service import (LocalAgreement, SegmenterConfig,
                                                   UtteranceSegmenter)
from backend.services.transcription_service import LivePipeline

SPEECH = np.full(BLOCK, 0.2, dtype=np.float32)
SILENCE = np.zeros(BLOCK, dtype=np.float32)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def make_settings(tmp: Path, **overrides: object) -> Settings:
    """Session-only settings, so tests never touch the real settings.json."""
    settings = Settings(tmp / "settings.json", catalog=available_engines)
    settings.apply_cli({"silence_hang": 0.7, **overrides})
    return settings


class FakeEngine:
    """Deterministic decoder: one word per 0.25s of audio."""

    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, audio: np.ndarray, config=None) -> tuple[str, float]:
        self.calls += 1
        words = max(0, int(audio.size / SAMPLE_RATE * 4))
        return " ".join(f"w{i}" for i in range(1, words + 1)), 0.1


class FakeMic:
    def __init__(self, frames: list[np.ndarray], delay: float = 0.01) -> None:
        self._frames = deque(frames)
        self._delay = delay

    def __enter__(self) -> "FakeMic":
        return self

    def __exit__(self, *exc) -> None:
        pass

    def read(self, timeout: float = 0.2) -> np.ndarray | None:
        if self._frames:
            frame = self._frames.popleft()
            time.sleep(self._delay)
            return frame
        time.sleep(timeout)
        return None


def _collect_until(subscriber, predicate, timeout: float) -> list[dict]:
    events: list[dict] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            event = subscriber.get(timeout=0.2)
        except queue.Empty:
            continue
        events.append(event)
        if predicate(event):
            return events
    raise AssertionError(f"timeout after {timeout}s (got {[e['type'] for e in events]})")


def _drain(subscriber, seconds: float) -> list[dict]:
    events: list[dict] = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            events.append(subscriber.get(timeout=0.1))
        except queue.Empty:
            continue
    return events


# --------------------------------------------------------------------------
# 1. Segmentation
# --------------------------------------------------------------------------
def test_segmenter() -> None:
    segmenter = UtteranceSegmenter()
    results = [segmenter.push(f) for f in [SILENCE] * 3 + [SPEECH] * 20 + [SILENCE] * 8]
    finals = [r for r in results if r is not None]
    assert len(finals) == 1, f"expected 1 utterance, got {len(finals)}"
    duration = finals[0].audio.size / SAMPLE_RATE
    assert finals[0].hard_end, "trailing silence must close the utterance"
    assert 2.9 <= duration <= 3.1, f"unexpected duration {duration:.2f}s"
    print(f"[1a] Segmenter OK - {duration:.2f}s utterance closed by silence")

    segmenter = UtteranceSegmenter()
    assert all(segmenter.push(f) is None for f in [SPEECH] + [SILENCE] * 8)
    print("[1b] Segmenter OK - short blip discarded")

    segmenter = UtteranceSegmenter(SegmenterConfig(max_utterance=1.0, silence_hang=99.0))
    flushes = [r for r in (segmenter.push(SPEECH) for _ in range(12)) if r is not None]
    assert len(flushes) == 1 and not flushes[0].hard_end
    assert abs(flushes[0].audio.size / SAMPLE_RATE - 1.0) < 0.15
    print("[1c] Segmenter OK - long speech flushed at max_utterance")

    segmenter = UtteranceSegmenter()
    for _ in range(4):
        segmenter.push(SPEECH)
    assert segmenter.snapshot() is not None and segmenter.speaking
    for _ in range(8):
        segmenter.push(SILENCE)
    assert segmenter.snapshot() is None
    print("[1d] Segmenter OK - snapshot grows then clears")

    segmenter = UtteranceSegmenter()
    for _ in range(5):
        segmenter.push(SPEECH)
    assert segmenter.flush() is not None, "flush must close an open utterance"
    print("[1e] Segmenter OK - flush closes the tail (file replay)")


# --------------------------------------------------------------------------
# 2. Local agreement
# --------------------------------------------------------------------------
def test_gate_warm_after_pause() -> None:
    """Pause must not freeze the gate: resume must detect speech immediately."""
    from backend.services.segmentation_service import EnergyGate

    gate = EnergyGate()
    # loud ambient / speech before the user hit pause
    for _ in range(100):
        gate.is_speech(0.05, False)
    # paused: quiet room, the gate must keep observing
    for _ in range(60):
        gate.observe(0.003)
    assert not gate.is_speech(0.01, False), "stale peak window should still block quiet speech"
    gate.resume()  # this is what the pipeline does when the user hits resume
    assert gate.is_speech(0.01, False), "gate stayed deaf after resume"
    assert gate.is_speech(0.05, False), "loud speech must still be detected"
    print("[2b] EnergyGate OK - stays warm across pause/resume")


def test_local_agreement() -> None:
    agreement = LocalAgreement()
    assert agreement.update("xin chào") == ("", "xin chào")
    assert agreement.update("xin chào các bạn") == ("xin chào", "các bạn")
    assert agreement.update("xin chào các bạn hôm nay") == ("xin chào các bạn", "hôm nay")
    assert agreement.update("xin chào các bạn hôm nay") == ("xin chào các bạn hôm nay", "")

    stable, tentative = agreement.update("xin chào các bạn hôm qua")
    assert stable == "xin chào các bạn hôm nay"
    assert tentative == "qua", tentative
    agreement.reset()
    assert agreement.stable_text == ""
    print("[2] LocalAgreement OK - commits on agreement, keeps revisions in draft")


# --------------------------------------------------------------------------
# 3-5. Pipeline modes / clear
# --------------------------------------------------------------------------
def test_pipeline_accurate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(Path(tmp))
        bus = EventBus()
        subscriber = bus.subscribe()
        frames = [SILENCE] * 3 + [SPEECH] * 20 + [SILENCE] * 8
        pipeline = LivePipeline(FakeEngine(), bus, settings,
                                mic_factory=lambda device: FakeMic(frames),
                                engine_factory=lambda values: FakeEngine())
        pipeline.start()
        try:
            events = _collect_until(subscriber, lambda e: e["type"] == "final", 8.0)
        finally:
            pipeline.stop()
            bus.unsubscribe(subscriber)

        finals = [e for e in events if e["type"] == "final"]
        assert finals and finals[0]["text"], "no final transcript"
        assert finals[0]["hard"] is True
        assert not [e for e in events if e["type"] == "partial"], \
            "accurate mode must not emit drafts"
        levels = [e for e in events if e["type"] == "level"]
        assert levels, "no level events for the meter"
        print(f"[3] Pipeline OK - accurate mode, final='{finals[0]['text']}', "
              f"{len(levels)} level frames")


def test_pipeline_realtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(Path(tmp), mode="realtime", decode_interval=0.2)
        bus = EventBus()
        subscriber = bus.subscribe()
        frames = [SILENCE] * 3 + [SPEECH] * 20 + [SILENCE] * 8
        pipeline = LivePipeline(FakeEngine(), bus, settings,
                                mic_factory=lambda device: FakeMic(frames),
                                engine_factory=lambda values: FakeEngine())
        pipeline.start()
        try:
            events = _collect_until(subscriber, lambda e: e["type"] == "final", 8.0)
        finally:
            pipeline.stop()
            bus.unsubscribe(subscriber)

        partials = [e for e in events
                    if e["type"] == "partial" and (e["stable"] or e["tentative"])]
        finals = [e for e in events if e["type"] == "final"]
        assert partials, "realtime mode must emit drafts"
        assert finals and finals[-1]["text"]
        print(f"[4] Pipeline OK - realtime mode, {len(partials)} drafts then final")


class BlockingEngine(FakeEngine):
    """Holds the decode thread mid-flight so we can clear while it is busy."""

    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def transcribe(self, audio: np.ndarray, config=None) -> tuple[str, float]:
        self.started.set()
        self.release.wait(3.0)
        return "xin chào các bạn", 0.1


def test_clear_drops_inflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(Path(tmp))
        bus = EventBus()
        subscriber = bus.subscribe()
        engine = BlockingEngine()
        pipeline = LivePipeline(engine, bus, settings,
                                mic_factory=lambda device: FakeMic(
                                    [SPEECH] * 12 + [SILENCE] * 8),
                                engine_factory=lambda values: FakeEngine())
        pipeline.start()
        try:
            assert engine.started.wait(3.0), "the decode worker never called the engine"
            time.sleep(0.35)  # let capture finish so nothing new is queued after the clear
            pipeline.clear()
            engine.release.set()
            events = _drain(subscriber, seconds=1.0)
        finally:
            pipeline.stop()
            bus.unsubscribe(subscriber)

        assert any(e["type"] == "clear" for e in events), "clear was not published"
        clear_index = next(i for i, e in enumerate(events) if e["type"] == "clear")
        leaked = [e for e in events[clear_index + 1:] if e["type"] in ("partial", "final")]
        assert not leaked, f"text leaked in after clear: {leaked}"
        print("[5] Pipeline OK - clear discards the in-flight decode")


# --------------------------------------------------------------------------
# 6. Engine reload
# --------------------------------------------------------------------------
def test_engine_reload() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(Path(tmp))
        bus = EventBus()
        subscriber = bus.subscribe()
        built: list[int] = []

        def factory(values):
            built.append(values["cpu_threads"])
            return FakeEngine()

        pipeline = LivePipeline(FakeEngine(), bus, settings,
                                mic_factory=lambda device: FakeMic([]),
                                engine_factory=factory)
        try:
            result = pipeline.apply({"cpu_threads": 3})
            assert result["effects"]["engine"] == ["cpu_threads"]
            events = _collect_until(
                subscriber,
                lambda e: e["type"] == "engine" and e["state"] == "ready", 5.0)
        finally:
            bus.unsubscribe(subscriber)

        assert built == [3], built
        ready = [e for e in events if e["type"] == "engine"][-1]
        assert ready["state"] == "ready"
        assert pipeline.engine_info()["state"] == "ready"
        print("[6] Pipeline OK - engine reloaded in the background")


# --------------------------------------------------------------------------
# 7. Replay
# --------------------------------------------------------------------------
def test_zipformer() -> None:
    """Optional: only runs when models/sherpa contains the zipformer files."""
    if not (MODEL_DIR / "encoder.int8.onnx").is_file():
        print("[7a] Zipformer SKIP - model not downloaded")
        return
    engine = create_engine("zipformer-vi-30M", {"cpu_threads": 2})
    text, rtf = engine.transcribe(np.zeros(SAMPLE_RATE, np.float32))
    assert isinstance(text, str) and rtf >= 0
    info = engine.describe()
    assert info["model"] and info["cpu_threads"] == 2
    print(f"[7a] Zipformer OK - 1s silence -> '{text}' (RTF {rtf:.2f})")


def test_engine_registry() -> None:
    """A new plugin only needs a class with key/label/transcribe."""

    class EchoEngine(ASREngine):
        key = "echo-test"
        label = "Echo (test)"

        @classmethod
        def fields(cls):
            from backend.config.fields import Field

            return (Field("gain", "engine", "Gain", "float", 1.0,
                          minimum=0.0, maximum=2.0, step=0.1),)

        def transcribe(self, audio):
            return f"echo {audio.size}", 0.01

    register_engine(EchoEngine)
    specs = available_engines()
    assert "echo-test" in specs and specs["echo-test"].available
    assert specs["echo-test"].fields[0].key == "gain"

    engine = create_engine("echo-test", {"cpu_threads": 1})
    assert engine.transcribe(np.zeros(BLOCK, np.float32))[0].startswith("echo")

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(Path(tmp) / "s.json", catalog=available_engines)
        result = settings.update({"model": "echo-test", "gain": 0.3})
        keys = {field["key"] for field in settings.schema()}
        assert "gain" in keys, "engine fields appear after switching model"
        assert result["values"]["gain"] == 0.3
    print("[7b] Registry OK - custom engine discovered, selectable, schema adapted")


def write_tone(path: Path, seconds: float = 1.2) -> None:
    samples = (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(seconds * SAMPLE_RATE))
                           / SAMPLE_RATE) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(samples.tobytes())


def test_replay() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = make_settings(root, min_speech=0.1, silence_hang=0.4)
        decode = lambda audio: (f"len{audio.size}", 0.01)
        service = ReplayService(decode, settings, root / "samples")
        write_tone(root / "samples" / "tone.wav")

        names = [item["name"] for item in service.list_samples()]
        assert names == ["tone.wav"], names

        result = service.run("tone.wav")
        assert result.text.startswith("len"), result.text
        assert 1.0 < result.audio_s < 1.4, result.audio_s
        assert result.decode_s >= 0 and result.rtf >= 0
        assert isinstance(result, ReplayResult)

        segmented = service.run("tone.wav", segment=True)
        assert segmented.segments, "segment=True must produce chunks"
        assert segmented.text, segmented.text

        payload = b"RIFFfake"
        entry = service.save_upload("../../evil.wav", payload)
        assert entry["name"] == "evil.wav", "upload must drop the path"
        assert (root / "samples" / "evil.wav").read_bytes() == payload

        try:
            service.save_upload("note.txt", b"x")
        except ValueError:
            pass
        else:
            raise AssertionError("non-audio upload must be rejected")

        try:
            service.run("../../../etc/passwd")
        except ValueError:
            pass
        else:
            raise AssertionError("path traversal must be rejected")
        print("[7] Replay OK - list, decode, segment and upload sanitiser")


# --------------------------------------------------------------------------
# 8. HTTP surface (FastAPI TestClient)
# --------------------------------------------------------------------------
def test_webapp() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = make_settings(root)
        bus = EventBus()
        pipeline = LivePipeline(FakeEngine(), bus, settings,
                                mic_factory=lambda device: FakeMic([]),
                                engine_factory=lambda values: FakeEngine())
        replay = ReplayService(lambda audio: ("xin chào", 0.01), settings, root / "samples")
        write_tone(root / "samples" / "tone.wav")
        app = create_app(settings, pipeline, replay, bus)

        with TestClient(app) as client:
            page = client.get("/")
            assert page.status_code == 200 and "STT Trực Tiếp" in page.text

            state = client.get("/api/state").json()
            assert state["type"] == "state" and "engine" in state and "capture" in state

            health = client.get("/api/health").json()
            assert health["ok"] is True

            payload = client.get("/api/settings").json()
            assert payload["values"]["mode"] == "accurate"
            assert payload["fields"], "settings schema must be served"
            assert any(field["key"] == "model" for field in payload["fields"])
            assert payload["engines"], "engine catalog must be listed"

            updated = client.post("/api/settings", json={"silence_hang": 1.1}).json()
            assert updated["values"]["silence_hang"] == 1.1

            invalid = client.post("/api/settings", json={"bogus": 1}).json()
            assert "bogus" in invalid["rejected"]

            devices = client.get("/api/devices").json()
            assert isinstance(devices["devices"], list)

            samples = client.get("/api/samples").json()
            assert [s["name"] for s in samples["samples"]] == ["tone.wav"]

            wav_bytes = (root / "samples" / "tone.wav").read_bytes()
            uploaded = client.post("/api/samples", files={
                "file": ("copy.wav", wav_bytes, "audio/wav")}).json()
            assert uploaded["ok"] and uploaded["name"] == "copy.wav"

            replay_result = client.post("/api/replay",
                                        json={"name": "tone.wav", "segment": True}).json()
            assert replay_result["ok"] and replay_result["text"]

            paused = client.post("/api/pause", json={"paused": True}).json()
            assert paused == {"ok": True, "paused": True}

            reset = client.post("/api/settings/reset").json()
            assert reset["values"]["mode"] == "accurate" and reset["fields"]

            with client.stream("GET", "/events") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                first = next(response.iter_lines())
                assert first.startswith("data: ")
        print("[8] API OK - page, state, health, settings, devices, samples, "
              "replay, pause, reset, SSE")


if __name__ == "__main__":
    test_segmenter()
    test_gate_warm_after_pause()
    test_local_agreement()
    test_pipeline_accurate()
    test_pipeline_realtime()
    test_clear_drops_inflight()
    test_engine_reload()
    test_zipformer()
    test_engine_registry()
    test_replay()
    test_webapp()
    print("TEST_STREAMING_DONE")
