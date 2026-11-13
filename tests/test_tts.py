"""TTS layer tests: WAV packaging, voice catalog and HTTP contract.

The real VieNeu model is not loaded here (first load takes ~10-20 s); the HTTP
tests inject a fake service. Run the real smoke check with:

    VIENEU_SMOKE=1 python -m pytest tests/test_tts.py
"""

from __future__ import annotations

import io
import os
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.paths import VIENEU_CUSTOM_VOICES
from backend.main import create_app
from backend.services.tts_service import (MAX_TTS_CHARS, TtsService, TtsUnavailable,
                                          _to_wav)

TINY_WAV = _to_wav(np.zeros(480, dtype=np.float32), 48_000)


class FakeTts:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def available(self) -> tuple[bool, str]:
        return (True, "") if self._available else (False, "chưa cài package 'vieneu'")

    def voices(self) -> tuple[list[dict], str]:
        return ([{"id": "Mai Anh", "label": "Mai Anh", "gender": "Nữ",
                  "featured": True, "custom": False}], "Mai Anh")

    def status(self) -> dict:
        return {"available": self._available, "loaded": False, "offline": True,
                "local_model": True, "max_chars": MAX_TTS_CHARS}

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, float]:
        if not self._available:
            raise TtsUnavailable("chưa cài package 'vieneu'")
        value = (text or "").strip()
        if not value:
            raise ValueError("chưa có văn bản để đọc")
        if len(value) > MAX_TTS_CHARS:
            raise ValueError(f"văn bản quá dài (tối đa {MAX_TTS_CHARS} ký tự)")
        return TINY_WAV, 0.01


class StubPipeline:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def make_client(tts: FakeTts) -> TestClient:
    app = create_app(None, StubPipeline(), None, None, tts=tts)  # type: ignore[arg-type]
    return TestClient(app)


# --------------------------------------------------------------------------
# 1. WAV packaging
# --------------------------------------------------------------------------
def test_wav_packaging() -> None:
    audio = (0.5 * np.sin(np.linspace(0, 20, 4_800))).astype(np.float32)
    payload = _to_wav(audio, 48_000)
    assert payload[:4] == b"RIFF"

    with wave.open(io.BytesIO(payload), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 48_000
        assert handle.getnframes() == 4_800


def test_wav_clips_out_of_range() -> None:
    payload = _to_wav(np.array([-3.0, 0.0, 3.0], dtype=np.float32), 16_000)
    with wave.open(io.BytesIO(payload), "rb") as handle:
        pcm = np.frombuffer(handle.readframes(3), dtype="<i2")
    assert pcm[0] == -32767 and pcm[1] == 0 and pcm[2] == 32767


# --------------------------------------------------------------------------
# 2. Voice catalog (real package assets, no model load)
# --------------------------------------------------------------------------
@pytest.mark.skipif(not TtsService.package_installed(), reason="vieneu not installed")
def test_voice_catalog_reads_presets() -> None:
    service = TtsService()
    voices, default = service.voices()

    assert len(voices) >= 20, "VieNeu ships a preset catalog"
    assert default and default in {entry["id"] for entry in voices}
    assert voices[0]["featured"] is True, "editors' picks come first"
    assert all(entry["label"] and entry["id"] for entry in voices)


@pytest.mark.skipif(not TtsService.package_installed(), reason="vieneu not installed")
@pytest.mark.skipif(not VIENEU_CUSTOM_VOICES.is_file(), reason="no cloned voices installed")
def test_voice_catalog_merges_cloned_voices() -> None:
    voices, _ = TtsService().voices()
    custom = [entry for entry in voices if entry["custom"]]
    assert custom, "custom_voices.json must show up in the catalog"


@pytest.mark.skipif(not TtsService.package_installed(), reason="vieneu not installed")
def test_local_model_is_detected() -> None:
    status = TtsService().status()
    assert status["local_model"] is True
    assert status["offline"] is True
    assert status["sample_rate"] == 48_000


@pytest.mark.skipif(not TtsService.package_installed(), reason="vieneu not installed")
def test_invalid_voice_is_rejected_before_loading() -> None:
    with pytest.raises(ValueError):
        TtsService().synthesize("xin chào", voice="không có giọng này")


def test_empty_text_is_rejected() -> None:
    with pytest.raises(ValueError):
        TtsService().synthesize("   ")


# --------------------------------------------------------------------------
# 3. HTTP contract
# --------------------------------------------------------------------------
def test_tts_voices_endpoint() -> None:
    with make_client(FakeTts()) as client:
        response = client.get("/api/tts/voices")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["default"] == "Mai Anh"
        assert body["voices"][0]["id"] == "Mai Anh"
        assert body["available"] is True


def test_tts_unavailable_is_503() -> None:
    with make_client(FakeTts(available=False)) as client:
        catalog = client.get("/api/tts/voices").json()
        assert catalog["available"] is False and catalog["reason"]

        response = client.post("/api/tts", json={"text": "xin chào"})
        assert response.status_code == 503
        assert response.json()["ok"] is False


def test_tts_returns_wav() -> None:
    with make_client(FakeTts()) as client:
        response = client.post("/api/tts", json={"text": "xin chào", "voice": "Mai Anh"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/wav")
        assert response.headers["X-Audio-Seconds"] == "0.01"
        assert response.content[:4] == b"RIFF"


def test_tts_rejects_empty_and_long_text() -> None:
    with make_client(FakeTts()) as client:
        empty = client.post("/api/tts", json={"text": "  "})
        assert empty.status_code == 400
        assert empty.json()["ok"] is False

        long = client.post("/api/tts", json={"text": "a" * (MAX_TTS_CHARS + 1)})
        assert long.status_code == 400


# --------------------------------------------------------------------------
# 4. Optional real synthesis (slow, needs the installed model)
# --------------------------------------------------------------------------
@pytest.mark.skipif(os.environ.get("VIENEU_SMOKE") != "1", reason="set VIENEU_SMOKE=1")
def test_real_synthesis_smoke() -> None:
    service = TtsService()
    payload, seconds = service.synthesize("Xin chào, đây là giọng đọc thử nghiệm.")
    assert payload[:4] == b"RIFF"
    assert seconds > 0.5
    assert service.status()["loaded"] is True


if __name__ == "__main__":
    test_wav_packaging()
    test_wav_clips_out_of_range()
    if TtsService.package_installed():
        test_voice_catalog_reads_presets()
        if VIENEU_CUSTOM_VOICES.is_file():
            test_voice_catalog_merges_cloned_voices()
        test_local_model_is_detected()
        test_invalid_voice_is_rejected_before_loading()
    test_empty_text_is_rejected()
    test_tts_voices_endpoint()
    test_tts_unavailable_is_503()
    test_tts_returns_wav()
    test_tts_rejects_empty_and_long_text()
    if os.environ.get("VIENEU_SMOKE") == "1":
        test_real_synthesis_smoke()
    print("TEST_TTS_DONE")
