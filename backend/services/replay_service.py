"""Offline replay of sample audio files - A/B test settings without speaking.

One responsibility: manage the sample folder and decode a file with whatever
settings are active right now, returning text plus timing so two configurations
can be compared on identical audio.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ..config.constants import BLOCK, BYTES_PER_MB, SAMPLE_RATE
from ..config.settings import Settings
from ..models.dto import ReplayResult, ReplaySegment
from .segmentation_service import build_segmenter

AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aac"})
MAX_UPLOAD_BYTES = 50 * BYTES_PER_MB
MAX_REPLAY_SECONDS = 300.0


class ReplayService:
    """Owns the ``samples/`` folder and the replay runs."""

    def __init__(self, decode: Callable[[np.ndarray], tuple[str, float]],
                 settings: Settings, samples_dir: Path | str) -> None:
        self._decode = decode
        self._settings = settings
        self._dir = Path(samples_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- folder ------------------------------------------------------------
    def list_samples(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self._dir.iterdir()):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                stat = path.stat()
                items.append({"name": path.name, "bytes": stat.st_size,
                              "modified": int(stat.st_mtime)})
        return items

    def save_upload(self, filename: str, data: bytes) -> dict[str, Any]:
        name = self._safe_name(filename)
        if not data:
            raise ValueError("file rỗng")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("file quá lớn (tối đa 50 MB)")
        target = self._unique_path(name)
        target.write_bytes(data)
        return {"name": target.name, "bytes": len(data)}

    # -- replay ------------------------------------------------------------
    def run(self, name: str, segment: bool = False) -> ReplayResult:
        path = self._resolve(name)
        audio = self._load(path)
        audio_s = audio.size / SAMPLE_RATE
        truncated = False
        limit = int(MAX_REPLAY_SECONDS * SAMPLE_RATE)
        if audio.size > limit:
            audio, truncated = audio[:limit], True

        started = time.perf_counter()
        chunks = self._segments(audio) if segment else [audio]
        items: list[ReplaySegment] = []
        for chunk in chunks:
            t0 = time.perf_counter()
            text, _ = self._decode(chunk)
            items.append(ReplaySegment(
                text=text,
                audio_s=round(chunk.size / SAMPLE_RATE, 2),
                decode_s=round(time.perf_counter() - t0, 3)))
        decode_s = time.perf_counter() - started
        text = " ".join(item.text for item in items if item.text).strip()
        return ReplayResult(
            name=path.name,
            text=text,
            segments=items,
            audio_s=round(audio_s, 2),
            decode_s=round(decode_s, 3),
            rtf=round(decode_s / max(audio_s, 1e-6), 3),
            truncated=truncated,
        )

    # -- helpers -----------------------------------------------------------
    def _segments(self, audio: np.ndarray) -> list[np.ndarray]:
        segmenter = build_segmenter(self._settings.values())
        chunks: list[np.ndarray] = []
        for start in range(0, audio.size, BLOCK):
            frame = audio[start:start + BLOCK]
            if frame.size < BLOCK:
                frame = np.pad(frame, (0, BLOCK - frame.size))
            closed = segmenter.push(frame.astype(np.float32))
            if closed is not None:
                chunks.append(closed.audio)
        tail = segmenter.flush()
        if tail is not None:
            chunks.append(tail.audio)
        return chunks

    def _load(self, path: Path) -> np.ndarray:
        """Read any audio file to 16 kHz mono float32.

        WAV goes through the stdlib (no dependency); everything else through
        PyAV, which ships with faster-whisper.
        """
        if path.suffix.lower() == ".wav":
            try:
                return self._load_wav(path)
            except Exception:
                pass  # e.g. float WAV: let PyAV try
        try:
            return self._load_av(path)
        except Exception as exc:
            raise ValueError(f"không đọc được file audio: {exc}") from exc

    def _load_wav(self, path: Path) -> np.ndarray:
        import wave

        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            raw = handle.readframes(handle.getnframes())
        audio = _pcm_to_float(raw, width)
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        return _resample(audio.astype(np.float32), rate)

    def _load_av(self, path: Path) -> np.ndarray:
        import av

        pieces: list[np.ndarray] = []
        with av.open(str(path)) as container:
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(format="flt", layout="mono",
                                          rate=SAMPLE_RATE)
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    pieces.append(out.to_ndarray().reshape(-1))
            for out in resampler.resample(None):
                pieces.append(out.to_ndarray().reshape(-1))
        if not pieces:
            raise ValueError("file không có âm thanh")
        return np.concatenate(pieces).astype(np.float32)

    def _safe_name(self, filename: str) -> str:
        name = Path(filename or "").name.strip()
        if not name:
            raise ValueError("thiếu tên file")
        if Path(name).suffix.lower() not in AUDIO_EXTENSIONS:
            raise ValueError("chỉ nhận file audio: " + ", ".join(sorted(AUDIO_EXTENSIONS)))
        return name

    def _unique_path(self, name: str) -> Path:
        target = self._dir / name
        if not target.exists():
            return target
        stem, suffix = Path(name).stem, Path(name).suffix
        for index in range(2, 1000):
            candidate = self._dir / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
        raise ValueError("quá nhiều file trùng tên")

    def _resolve(self, name: str) -> Path:
        safe = self._safe_name(name)
        path = self._dir / safe
        if not path.is_file():
            raise FileNotFoundError(f"không thấy file '{safe}' trong samples/")
        return path


def _pcm_to_float(raw: bytes, width: int) -> np.ndarray:
    """PCM bytes -> float32 in [-1, 1] (mono layout preserved)."""
    if width == 1:
        return (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    if width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if width == 3:
        triplets = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        value = triplets[:, 0] | (triplets[:, 1] << 8) | (triplets[:, 2] << 16)
        value = np.where(value & 0x800000, value - 0x1000000, value)
        return value.astype(np.float32) / 8388608.0
    if width == 4:
        return np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    raise ValueError(f"độ sâu PCM {width * 8} bit không hỗ trợ")


def _resample(audio: np.ndarray, rate: int) -> np.ndarray:
    if rate == SAMPLE_RATE or audio.size == 0:
        return audio
    count = max(1, int(round(audio.size * SAMPLE_RATE / rate)))
    positions = np.linspace(0, audio.size - 1, count, dtype=np.float64)
    return np.interp(positions, np.arange(audio.size), audio).astype(np.float32)
