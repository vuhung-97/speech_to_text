"""Block-wise PCM16 conversion and WAV headers.

The whole point of this module is to **never** materialise the full float32
waveform plus several full-size copies. Every conversion runs one 1-second block
at a time, so peak memory is ``input + output + one scratch block``.
"""

from __future__ import annotations

import io
import struct

import numpy as np

BLOCK_SAMPLES = 48_000  # 1 s at 48 kHz
WAV_HEADER_BYTES = 44
INT16_SCALE = 32767.0
_FMT = "<4sI4s4sIHHIIHH4sI"


def to_pcm16(block: np.ndarray | list[float]) -> bytes:
    """Mono float32 in [-1, 1] → interleaved little-endian PCM16 bytes."""
    data = np.asarray(block, dtype=np.float32).reshape(-1)
    if data.size == 0:
        return b""
    scaled = data * INT16_SCALE
    np.clip(scaled, -INT16_SCALE, INT16_SCALE, out=scaled)
    return scaled.astype("<i2").tobytes()


def pcm16_to_float(pcm: bytes) -> np.ndarray:
    """PCM16 bytes → float32 samples in [-1, 1] (used by tests and the player)."""
    if not pcm:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / INT16_SCALE


def wav_header(sample_rate: int, data_bytes: int = 0) -> bytes:
    """A 44-byte canonical mono PCM16 WAV header."""
    return struct.pack(
        _FMT,
        b"RIFF", 36 + data_bytes, b"WAVE",
        b"fmt ", 16, 1, 1, int(sample_rate),
        int(sample_rate) * 2, 2, 16,
        b"data", data_bytes,
    )


def patch_wav_sizes(handle: io.BufferedRandom) -> int:
    """Fill in RIFF/data sizes after the audio was appended; return data bytes.

    The file is created with a zero-filled header so synthesis can stream to
    disk without knowing the final length in advance. One file, no second copy.
    """
    end = handle.seek(0, io.SEEK_END)
    data_bytes = max(0, end - WAV_HEADER_BYTES)
    handle.seek(4)
    handle.write(struct.pack("<I", 36 + data_bytes))
    handle.seek(40)
    handle.write(struct.pack("<I", data_bytes))
    handle.seek(0, io.SEEK_END)
    handle.flush()
    return data_bytes


def silence_pcm(seconds: float, sample_rate: int) -> bytes:
    """Zero samples used as a breath between paragraphs."""
    count = max(0, int(round(seconds * sample_rate)))
    return b"\x00\x00" * count


def to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Whole waveform → WAV bytes, converted block by block.

    Used by the short path (≤1000 characters) where holding the result in memory
    is bounded and convenient. Peak is ~2.5× the audio instead of ~5×.
    """
    flat = np.asarray(audio, dtype=np.float32).reshape(-1)
    buffer = io.BytesIO()
    buffer.write(wav_header(sample_rate, flat.size * 2))
    for start in range(0, flat.size, BLOCK_SAMPLES):
        buffer.write(to_pcm16(flat[start:start + BLOCK_SAMPLES]))
    return buffer.getvalue()


__all__ = [
    "BLOCK_SAMPLES",
    "INT16_SCALE",
    "WAV_HEADER_BYTES",
    "patch_wav_sizes",
    "pcm16_to_float",
    "silence_pcm",
    "to_pcm16",
    "to_wav_bytes",
    "wav_header",
]
