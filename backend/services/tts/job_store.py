"""Long-form synthesis jobs: temp WAV storage, quota, TTL and cancellation.

One job at a time (the model is single-flight); finished WAVs stay readable for
the download route until the TTL or the disk quota removes them.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...config.paths import TTS_DISK_QUOTA_MB, TTS_TEMP_DIR
from ...config.constants import TTS_SAMPLE_RATE
from ..audio.temp_store import (TempAudioStore, TempSession,
                                cleanup_stale_sessions, free_bytes)
from .errors import TtsBusy, TtsCancelled, TtsStorageError

JOB_TTL_SECONDS = 1_800  # finished WAVs are removed after 30 minutes
CHARS_PER_SECOND = 11.7  # ~speech pace used for the disk estimate
DISK_HEADROOM_BYTES = 64 * 1024 * 1024


@dataclass
class SpeechJob:
    """One long-form synthesis: its temp session, growth state and cancel flag."""

    id: str
    session: TempSession
    store: TempAudioStore
    text: str
    voice: str | None
    estimated_seconds: float
    created_at: float = field(default_factory=time.time)
    cancelled: threading.Event = field(default_factory=threading.Event)
    started: bool = False
    finalized: bool = False

    @property
    def wav_path(self) -> Path:
        return self.store.path

    @property
    def seconds(self) -> float:
        return self.store.seconds

    @property
    def bytes(self) -> int:
        return self.store.size_bytes


class TtsJobStore:
    """Owns the job registry, the temp tree and the disk budget."""

    def __init__(
        self,
        temp_root: Path | str | None = None,
        quota_mb: int = TTS_DISK_QUOTA_MB,
        sample_rate: int = TTS_SAMPLE_RATE,
        ttl_seconds: float = JOB_TTL_SECONDS,
    ) -> None:
        self._temp_root = Path(temp_root) if temp_root else TTS_TEMP_DIR
        self._quota_bytes = max(1, int(quota_mb)) * 1024 * 1024
        self._bytes_per_second = int(sample_rate) * 2
        self._ttl = float(ttl_seconds)
        self._jobs: dict[str, SpeechJob] = {}
        self._lock = threading.Lock()
        self._active: SpeechJob | None = None

    # ------------------------------------------------------------------ reads
    @property
    def busy(self) -> bool:
        active = self._active
        return bool(active and not active.finalized and not active.cancelled.is_set())

    @property
    def active(self) -> SpeechJob | None:
        return self._active

    def values(self) -> list[SpeechJob]:
        """Snapshot of every tracked job (used by tests and housekeeping)."""
        with self._lock:
            return list(self._jobs.values())

    def get(self, job_id: str) -> SpeechJob | None:
        return self._jobs.get(job_id)

    def status(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        done = job.seconds
        estimate = max(job.estimated_seconds, 0.001)
        return {
            "id": job.id,
            "seconds": round(done, 2),
            "estimated_seconds": round(job.estimated_seconds, 1),
            "bytes": job.bytes,
            "sample_rate": TTS_SAMPLE_RATE,
            "finalized": job.finalized,
            "cancelled": job.cancelled.is_set(),
            "progress": round(min(1.0, done / estimate), 3),
        }

    def path(self, job_id: str) -> Path | None:
        job = self._jobs.get(job_id)
        if job is None or not job.finalized:
            return None
        return job.wav_path

    # ----------------------------------------------------------------- writes
    def create(self, text: str, voice: str | None,
               session_id: str | None = None) -> SpeechJob:
        """Validate the disk budget and reserve a temp session for one job."""
        if self.busy:
            raise TtsBusy("đang đọc một văn bản khác — dừng lại rồi thử tiếp")

        estimated = max(1.0, len(text) / CHARS_PER_SECOND)
        needed = int(estimated * self._bytes_per_second)
        self._prune_finished()
        if needed > self._quota_bytes:
            raise TtsStorageError(
                "văn bản vượt quá hạn mức đĩa cho phép — giảm bớt độ dài")
        self._evict_for_quota(needed)
        if free_bytes(self._temp_root) < needed + DISK_HEADROOM_BYTES:
            raise TtsStorageError(
                "không đủ dung lượng đĩa cho văn bản này — giảm bớt độ dài")

        session = TempSession(self._temp_root, session_id)
        store = session.store("audio", TTS_SAMPLE_RATE)
        job = SpeechJob(
            id=session.id,
            session=session,
            store=store,
            text=text,
            voice=voice,
            estimated_seconds=estimated,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._active = job
        return job

    def finish(self, job: SpeechJob, failed: bool) -> None:
        """Close a streamed job: drop it on failure, else keep the WAV."""
        with self._lock:
            if self._active is job:
                self._active = None
        if failed or job.cancelled.is_set():
            self._drop_job(job)
        elif not job.finalized:
            job.store.finalize()
            job.finalized = True

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.cancelled.set()
        job.store.fail(TtsCancelled("đã huỷ"))
        if job.finalized:
            self._drop_job(job)
        return True

    def shutdown(self) -> None:
        """Cancel every job and remove the whole temp tree (called on exit)."""
        with self._lock:
            jobs = list(self._jobs.values())
            self._jobs.clear()
            self._active = None
        for job in jobs:
            job.cancelled.set()
            job.session.cleanup()
        cleanup_stale_sessions(self._temp_root, max_age_hours=0)

    # ------------------------------------------------------------------ quota
    def _drop_job(self, job: SpeechJob) -> None:
        with self._lock:
            self._jobs.pop(job.id, None)
            if self._active is job:
                self._active = None
        job.session.cleanup()

    def _prune_finished(self) -> None:
        """Drop finished jobs (and their temp WAVs) older than the TTL."""
        cutoff = time.time() - self._ttl
        with self._lock:
            stale = [job for job in self._jobs.values()
                     if job.finalized and job is not self._active
                     and job.created_at < cutoff]
        for job in stale:
            self._drop_job(job)

    def _evict_for_quota(self, needed: int) -> None:
        """Delete the oldest finished jobs until ``needed`` bytes fit the quota."""
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at)
        total = sum(job.bytes for job in jobs)
        for job in jobs:
            if total + needed <= self._quota_bytes:
                break
            if job is self._active or not job.finalized:
                continue
            total -= job.bytes
            self._drop_job(job)


__all__ = ["JOB_TTL_SECONDS", "SpeechJob", "TtsJobStore"]
