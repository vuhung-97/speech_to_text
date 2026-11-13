"""PCM conversion: byte-identical to the previous implementation, bounded memory."""

from __future__ import annotations

import io
import sys
import tracemalloc
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.audio.pcm import (BLOCK_SAMPLES, pcm16_to_float, silence_pcm,
                                      to_pcm16, to_wav_bytes, wav_header)


def reference_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    """The pre-refactor implementation, kept as the compatibility oracle."""
    pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


@pytest.mark.parametrize("size", [0, 1, 2, BLOCK_SAMPLES - 1, BLOCK_SAMPLES,
                                  BLOCK_SAMPLES + 1, 3 * BLOCK_SAMPLES + 7])
def test_to_wav_is_byte_identical(size: int) -> None:
    rng = np.random.default_rng(7 + size)
    audio = rng.uniform(-1.2, 1.2, size).astype(np.float32)
    assert to_wav_bytes(audio, 48_000) == reference_wav(audio, 48_000)


def test_to_pcm16_clips_out_of_range() -> None:
    pcm = pcm16_to_float(to_pcm16(np.array([-3.0, 0.0, 3.0], dtype=np.float32)))
    assert pcm.tolist() == pytest.approx([-1.0, 0.0, 1.0])


def test_to_pcm16_empty() -> None:
    assert to_pcm16(np.zeros(0, dtype=np.float32)) == b""
    assert to_pcm16([]) == b""


def test_wav_header_is_valid_and_patchable() -> None:
    assert len(wav_header(48_000)) == 44
    payload = to_wav_bytes(np.zeros(1_000, dtype=np.float32), 48_000)
    with wave.open(io.BytesIO(payload), "rb") as handle:
        assert (handle.getnchannels(), handle.getsampwidth()) == (1, 2)
        assert handle.getframerate() == 48_000
        assert handle.getnframes() == 1_000


def test_silence_pcm_length() -> None:
    assert silence_pcm(0.5, 48_000) == b"\x00\x00" * 24_000
    assert silence_pcm(0, 48_000) == b""


def test_conversion_peak_memory_is_bounded() -> None:
    audio = np.zeros(90 * 48_000, dtype=np.float32)  # ~17 MB, ~1000 characters
    tracemalloc.start()
    payload = to_wav_bytes(audio, 48_000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert len(payload) == 44 + audio.size * 2
    assert peak < 50 * 2**20          # new implementation: ~34 MB
    assert peak < 3.2 * audio.nbytes  # old implementation was ~5×
