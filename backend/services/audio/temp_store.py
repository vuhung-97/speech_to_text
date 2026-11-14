"""Temporary audio storage (orchestration-level, filesystem I/O).

Long documents cannot live in RAM: two hours of 48 kHz float32 is ~1.38 GB,
and every concatenation would copy it. This store writes PCM16 (2 bytes/sample)
to a single WAV file as the model produces audio, reads it back by seeking, and
lets an HTTP reader follow the growing file through a condition variable.

Windows notes: the writer and reader use two handles on purpose (seek on a
shared handle would corrupt the write position), and the directory is removed
only after both handles are closed.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
import uuid
from pathlib import Path

import numpy as np

from ...domain.audio.pcm import (WAV_HEADER_BYTES, patch_wav_sizes, to_pcm16,
                                 wav_header)

DISK_MODE_MIN_CHARS = 20_000  # aligned with the long-form character ceiling


class TempAudioStore:
    """A WAV file that grows while the synthesizer appends PCM16 blocks."""

    def __init__(self, path: str | Path, sample_rate: int) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sample_rate = int(sample_rate)
        self._wfh = open(self.path, "w+b")
        self._wfh.write(wav_header(self.sample_rate, 0))
        self._wfh.flush()
        self._rfh = open(self.path, "rb")
        self._samples = 0
        self._finalized = False
        self._closed = False
        self._error: BaseException | None = None
        self._cond = threading.Condition()

    # ------------------------------------------------------------ properties
    @property
    def total_samples(self) -> int:
        return self._samples

    def __len__(self) -> int:
        return self._samples

    @property
    def size_bytes(self) -> int:
        return self._samples * 2

    @property
    def seconds(self) -> float:
        return self._samples / float(self.sample_rate or 1)

    @property
    def finalized(self) -> bool:
        return self._finalized

    @property
    def closed(self) -> bool:
        return self._closed

    # ----------------------------------------------------------------- write
    def append_pcm(self, pcm: bytes) -> int:
        """Append already-converted PCM16 bytes; returns the new sample count."""
        if not pcm or self._closed:
            return self._samples
        if len(pcm) % 2:
            pcm = pcm[:-1]
        with self._cond:
            if self._error is not None:
                raise RuntimeError("luồng ghi audio đã dừng") from self._error
            self._wfh.write(pcm)
            self._samples += len(pcm) // 2
            self._cond.notify_all()
        return self._samples

    def append(self, chunk: np.ndarray) -> int:
        """Append float32 samples (converted block-wise, no full-size copy)."""
        return self.append_pcm(to_pcm16(chunk))

    # ------------------------------------------------------------------ read
    def read_pcm(self, start_sample: int, n_samples: int) -> bytes:
        """Read ``n_samples`` from ``start_sample``; never raises on overrun."""
        with self._cond:
            return self._read_locked(start_sample, n_samples)

    def _read_locked(self, start_sample: int, n_samples: int) -> bytes:
        if self._closed or n_samples <= 0:
            return b""
        start = max(0, int(start_sample))
        if start >= self._samples:
            return b""
        count = min(int(n_samples), self._samples - start)
        try:
            self._wfh.flush()
        except (ValueError, OSError):
            return b""
        self._rfh.seek(WAV_HEADER_BYTES + start * 2)
        return self._rfh.read(count * 2)

    def read_available(self, start_sample: int, timeout: float = 1.0) -> bytes:
        """Block until new samples exist (or the stream ends), then read the rest."""
        with self._cond:
            if self._samples <= start_sample and not self._finalized:
                self._cond.wait(timeout)
            return self._read_locked(start_sample, self._samples - start_sample)

    def read_float(self, start_sample: int, n_samples: int) -> np.ndarray:
        from ...domain.audio.pcm import pcm16_to_float

        return pcm16_to_float(self.read_pcm(start_sample, n_samples))

    # -------------------------------------------------------------- lifecycle
    def finalize(self) -> int:
        """Patch the WAV sizes and wake every reader waiting for an end."""
        with self._cond:
            if self._finalized or self._closed:
                return self._samples
            try:
                patch_wav_sizes(self._wfh)
            finally:
                self._finalized = True
                self._cond.notify_all()
            return self._samples

    def fail(self, error: BaseException) -> None:
        """Record a synthesis failure so waiting readers stop instead of hanging."""
        with self._cond:
            self._error = error
            self._finalized = True
            self._cond.notify_all()

    def close(self) -> None:
        with self._cond:
            if self._closed:
                return
            self._closed = True
            self._finalized = True
            for handle in (self._wfh, self._rfh):
                try:
                    handle.flush()
                    handle.close()
                except Exception:
                    pass
            self._cond.notify_all()

    def cleanup(self, remove_dir: bool = True) -> None:
        self.close()
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
        if remove_dir:
            try:
                parent = self.path.parent
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass


class TempSession:
    """One directory per speech job (``<root>/<session_id>/``)."""

    def __init__(self, root: str | Path, session_id: str | None = None) -> None:
        self.id = session_id or f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        self.dir = Path(root) / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._stores: list[TempAudioStore] = []

    def store(self, name: str, sample_rate: int) -> TempAudioStore:
        store = TempAudioStore(self.dir / f"{name}.wav", sample_rate)
        self._stores.append(store)
        return store

    @property
    def path(self) -> Path:
        return self.dir

    def cleanup(self) -> None:
        for store in self._stores:
            store.close()
        self._stores.clear()
        shutil.rmtree(self.dir, ignore_errors=True)

    def __enter__(self) -> "TempSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.cleanup()


# --------------------------------------------------------------------- housekeeping
def directory_bytes(path: Path, limit: int = 5_000) -> int:
    """Total size of files under ``path`` (shallow guard against huge trees)."""
    total = 0
    try:
        for index, entry in enumerate(path.rglob("*")):
            if index > limit:
                break
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
    except OSError:
        return total
    return total


def cleanup_stale_sessions(root: str | Path, max_age_hours: float = 24.0) -> int:
    """Remove session directories left behind by a killed process."""
    folder = Path(root)
    if not folder.is_dir():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for entry in folder.iterdir():
        if not entry.is_dir():
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


def should_use_disk(text: str, mode: str = "auto") -> bool:
    """``mode`` is ``auto`` (by length), ``memory`` or ``disk``."""
    if mode == "disk":
        return True
    if mode == "memory":
        return False
    return len(text or "") >= DISK_MODE_MIN_CHARS


def free_bytes(path: str | Path) -> int:
    target = Path(path)
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        return shutil.disk_usage(str(target)).free
    except OSError:
        return 0


__all__ = [
    "DISK_MODE_MIN_CHARS",
    "TempAudioStore",
    "TempSession",
    "cleanup_stale_sessions",
    "directory_bytes",
    "free_bytes",
    "should_use_disk",
]
