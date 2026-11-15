"""Threading glue: microphone -> segmenter -> decode worker -> event bus.

Responsibilities stay separated: the engine only decodes audio, the segmenter
only decides where an utterance starts/ends, and this module only moves data
between them, applies settings changes and publishes events for the UI.

Two modes:

    accurate  one decode per utterance, model quality first (default)
    realtime  re-decode every ``decode_interval`` for a live draft (LocalAgreement)

Settings changes with ``effect == "engine"`` rebuild the ASR engine (any plugin)
on a background thread and swap it atomically; capture settings reopen the mic.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np

from ..config.constants import BLOCK_DUR
from ..config.settings import Settings
from ..models.dto import CaptureStats
from ..utils import priority
from .capture_service import MicStream
from .engines import ASREngine, create_engine
from .event_service import Event, EventBus
from .segmentation_service import (FinalAudio, LocalAgreement, UtteranceSegmenter,
                                   build_segmenter)

VAD_KEYS = frozenset({"silence_hang", "threshold", "noise_floor_ratio",
                      "min_speech", "preroll", "max_utterance"})


class _Job:
    __slots__ = ("audio", "hard", "gen")

    def __init__(self, audio: np.ndarray, hard: bool | None, gen: int) -> None:
        self.audio = audio
        self.hard = hard  # None => live draft, True/False => closing decode
        self.gen = gen


def default_engine_factory(values: dict[str, Any]) -> ASREngine:
    """Build the engine selected in settings (any registered plugin)."""
    return create_engine(str(values["model"]), values)


class LivePipeline:
    """One responsibility: run the live speech-to-text loop in the background."""

    def __init__(
        self,
        engine: Any,
        bus: EventBus,
        settings: Settings,
        *,
        mic_factory: Callable[[int | str | None], Any] = MicStream,
        engine_factory: Callable[[dict[str, Any]], Any] | None = None,
        transcribe_lock: threading.Lock | None = None,
        start_listening: bool = True,
    ) -> None:
        self._bus = bus
        self._settings = settings
        self._values = settings.values()
        self._mic_factory = mic_factory
        self._engine_factory = engine_factory or default_engine_factory
        self._engine = engine
        self._engine_info: dict[str, Any] = (
            engine.describe() if hasattr(engine, "describe") else {})
        self._engine_state = "ready"
        self._reload_token = 0
        self._transcribe_lock = transcribe_lock or threading.Lock()  # one model call at a time

        self._segmenter = build_segmenter(self._values)
        self._agreement = LocalAgreement()

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._listen = threading.Event()
        if start_listening:
            self._listen.set()  # tests/direct use listen; the web app passes False
        self._restart_capture = threading.Event()
        self._cv = threading.Condition()
        self._partial: np.ndarray | None = None
        self._finals: deque[_Job] = deque(maxlen=int(self._values["queue_size"]))
        self._frames_since_decode = 0
        self._generation = 0  # bumped on clear so in-flight decodes are dropped

        self._state = "starting"
        self._state_lock = threading.Lock()
        self._rtf: float | None = None
        self._mic: Any | None = None
        self._capture: dict[str, Any] = {}
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------ life
    def start(self) -> None:
        self._threads = [
            threading.Thread(target=self._capture_loop, name="stt-capture", daemon=True),
            threading.Thread(target=self._decode_loop, name="stt-decode", daemon=True),
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._cv:
            self._cv.notify_all()
        for thread in self._threads:
            thread.join(timeout=2.5)

    # --------------------------------------------------------------- control
    def set_paused(self, paused: bool) -> bool:
        if paused:
            self._listen.clear()
            self._pause.set()
            self._drop_in_progress()
            self._set_state("paused")
        else:
            self._listen.set()
            self._pause.clear()
            self._segmenter.gate.resume()
            self._set_state("listening")
        return self._pause.is_set()

    def set_listening(self, listening: bool) -> bool:
        """Open or close the microphone for real.

        Unlike a soft pause, closing releases the audio device: nothing is
        captured while the assistant is reading or the user is typing.
        """
        self.set_paused(not listening)
        return self._listen.is_set()

    def clear(self) -> None:
        with self._cv:
            self._generation += 1
            self._partial = None
            self._finals.clear()
        self._drop_in_progress()
        self._bus.publish({"type": "clear"})
        self._publish_queue()

    def decode(self, audio: np.ndarray) -> tuple[str, float]:
        """Decode arbitrary audio with the current engine (used by replay)."""
        with self._transcribe_lock:
            return self._engine.transcribe(audio)

    # -------------------------------------------------------------- settings
    def apply(self, patch: dict[str, Any]) -> dict[str, Any]:
        return self._commit(self._settings.update(patch))

    def reset_settings(self) -> dict[str, Any]:
        return self._commit(self._settings.reset())

    def _commit(self, result: dict[str, Any]) -> dict[str, Any]:
        values = result["values"]
        applied = set(result["applied"])
        effects = result["effects"]
        self._values = values

        if applied & VAD_KEYS or "mode" in applied:
            self._segmenter = build_segmenter(values)
            self._agreement.reset()
            self._drop_in_progress()
        if "queue_size" in applied:
            size = int(values["queue_size"])
            with self._cv:
                self._finals = deque(list(self._finals)[-size:], maxlen=size)
        if effects["engine"]:
            self._reload_engine(values)
        if effects["capture"]:
            self._restart_capture.set()
        self._bus.publish({"type": "settings", "values": values,
                           "warnings": self._settings.warnings()})
        return result

    def _reload_engine(self, values: dict[str, Any]) -> None:
        self._reload_token += 1
        token = self._reload_token
        self._engine_state = "loading"
        self._bus.publish({"type": "engine", "state": "loading"})

        def run() -> None:
            priority.lowest_for_background()
            t0 = time.perf_counter()
            try:
                new_engine = self._engine_factory(values)
            except Exception as exc:
                if token != self._reload_token:
                    return
                self._engine_state = "error"
                self._bus.publish({"type": "engine", "state": "error",
                                   "detail": str(exc).splitlines()[0] if str(exc) else "reload failed"})
                return
            if token != self._reload_token:
                return  # a newer reload superseded this one
            self._engine = new_engine
            self._engine_info = (new_engine.describe() if hasattr(new_engine, "describe")
                                 else {})
            self._engine_state = "ready"
            self._engine_info["reload_seconds"] = round(time.perf_counter() - t0, 2)
            self._bus.publish({"type": "engine", "state": "ready", **self._engine_info})

        threading.Thread(target=run, name="stt-reload", daemon=True).start()

    # ----------------------------------------------------------------- reads
    def status_event(self) -> Event:
        with self._state_lock:
            state = self._state
        return {"type": "status", "state": state, "paused": self._pause.is_set(),
                "listening": self._listen.is_set(),
                "rtf": self._rtf, "mode": self._values.get("mode")}

    def engine_info(self) -> dict[str, Any]:
        return {**self._engine_info, "state": self._engine_state}

    def capture_stats(self) -> CaptureStats:
        mic = self._mic
        if mic is not None and hasattr(mic, "stats"):
            try:
                return CaptureStats.from_stats(mic.stats())
            except Exception:
                pass
        return CaptureStats.from_stats(self._capture)

    def pending(self) -> int:
        with self._cv:
            return len(self._finals)

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def mode(self) -> str:
        return str(self._values.get("mode", "accurate"))

    def snapshot(self) -> dict[str, Any]:
        return {"type": "state", "status": self.status_event(),
                "engine": self.engine_info(), "capture": self.capture_stats().to_dict(),
                "queue": self.pending(), "settings": self._values,
                "warnings": self._settings.warnings()}

    # --------------------------------------------------------------- capture
    def _capture_loop(self) -> None:
        while not self._stop.is_set():
            self._restart_capture.clear()
            if not self._listen.is_set():
                # Microphone off: keep the device closed instead of reading and
                # discarding frames. This is what makes "reading" and
                # "listening" mutually exclusive.
                self._set_state("paused")
                self._listen.wait(0.1)
                continue
            device = self._values.get("device") or None
            try:
                with self._mic_factory(device) as mic:
                    self._mic = mic
                    if not self._pause.is_set():
                        self._set_state("listening")
                    while (not self._stop.is_set()
                           and not self._restart_capture.is_set()
                           and self._listen.is_set()):
                        frame = mic.read(timeout=0.2)
                        if frame is not None:
                            self._on_frame(frame)
                    self._remember_capture(mic)
            except Exception as exc:
                detail = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
                self._set_state("error")
                self._bus.publish({"type": "error", "detail": detail})
                if not self._stop.is_set() and not self._restart_capture.is_set():
                    self._stop.wait(1.5)  # do not hot-loop on a blocked mic
            finally:
                self._mic = None

    def _remember_capture(self, mic: Any) -> None:
        if hasattr(mic, "stats"):
            try:
                self._capture = dict(mic.stats())
            except Exception:
                pass

    def _on_frame(self, frame: np.ndarray) -> None:
        rms = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
        self._bus.publish({"type": "level", "value": round(rms, 4),
                           "speech": self._segmenter.speaking})

        if self._pause.is_set():
            # keep the VAD warm across pauses: a frozen gate would resume with a
            # stale 10 s peak window and miss the first seconds after resuming
            self._segmenter.gate.observe(rms)
            return

        final: FinalAudio | None = self._segmenter.push(frame)
        if final is not None:
            self._queue_final(final)
            return
        if self._values.get("mode") != "realtime" or not self._segmenter.speaking:
            return
        self._frames_since_decode += 1
        if self._frames_since_decode * BLOCK_DUR >= float(self._values["decode_interval"]):
            self._queue_partial()

    def _queue_partial(self) -> None:
        self._frames_since_decode = 0
        audio = self._segmenter.snapshot()
        if audio is None:
            return
        with self._cv:
            self._partial = audio  # newest snapshot wins, stale ones are dropped
            self._cv.notify()

    def _queue_final(self, final: FinalAudio) -> None:
        self._frames_since_decode = 0
        size = max(1, int(self._values.get("queue_size", 4)))
        with self._cv:
            self._partial = None  # the closed utterance supersedes any draft
            overflow = len(self._finals) >= size
            self._finals.append(_Job(final.audio, final.hard_end, self._generation))
            pending = len(self._finals)
            self._cv.notify()
        self._bus.publish({"type": "queue", "pending": pending})
        if overflow:
            self._bus.publish({"type": "warning",
                               "detail": "Hàng đợi đầy: câu cũ nhất đã bị bỏ"})

    # ---------------------------------------------------------------- decode
    def _decode_loop(self) -> None:
        priority.lower_for_decode()
        while not self._stop.is_set():
            job = self._next_job()
            if job is None:
                continue
            try:
                with self._transcribe_lock:
                    text, rtf = self._engine.transcribe(job.audio)
            except Exception as exc:
                self._bus.publish({"type": "error", "detail": f"decode failed: {exc}"})
                continue
            if job.gen != self._generation:
                continue  # cleared while decoding: discard the result
            self._rtf = round(rtf, 3)
            if job.hard is None:
                stable, tentative = self._agreement.update(text)
                self._bus.publish({"type": "partial", "stable": stable,
                                   "tentative": tentative, "rtf": self._rtf})
            else:
                self._finalize(text, job.hard)
            if not self._pause.is_set():
                self._set_state("listening")

    def _finalize(self, text: str, hard: bool) -> None:
        stable = self._agreement.stable_text
        self._agreement.reset()
        final_text = (text or stable).strip()
        self._publish_queue()
        if not final_text:
            return
        self._bus.publish({"type": "final", "text": final_text,
                           "hard": hard, "rtf": self._rtf})

    def _next_job(self) -> _Job | None:
        with self._cv:
            while not self._stop.is_set():
                if self._finals:
                    return self._finals.popleft()
                if self._partial is not None:
                    audio, self._partial = self._partial, None
                    return _Job(audio, None, self._generation)
                self._cv.wait(0.25)
        return None

    # --------------------------------------------------------------- helpers
    def _publish_queue(self) -> None:
        self._bus.publish({"type": "queue", "pending": self.pending()})

    def _drop_in_progress(self) -> None:
        self._segmenter.reset()
        self._agreement.reset()
        self._frames_since_decode = 0
        with self._cv:
            self._partial = None

    def _set_state(self, state: str) -> None:
        with self._state_lock:
            if state == self._state:
                return
            self._state = state
        self._bus.publish(self.status_event())
