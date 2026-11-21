"""Pre-render curated answers to WAV so a repeated question plays instantly.

One background job at a time (the TTS engine is single-flight anyway). The job
copies the finished temp WAV into ``data/audio`` (persistent, gitignored) and
records it in ``faq_audio``; the oldest files are evicted when the cache exceeds
its quota.
"""

from __future__ import annotations

import re
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..config.paths import AUDIO_CACHE_DIR
from ..domain.faq.models import FaqEntryNotFound
from ..ports.faq import FaqAudioRepository, FaqRepository
from ..ports.speech import SpeechSynthesizer
from ..services.tts_service import TtsBusy

MAX_CACHE_MB = 512
MAX_JOBS = 20
_VOICE_SAFE = re.compile(r"[^a-z0-9_-]+")


@dataclass
class FaqAudioJob:
    id: str
    entry_id: str
    tenant: str
    voice: str
    status: str = "running"  # running | done | error
    seconds: float = 0.0
    error: str = ""
    started_at: float = field(default_factory=time.time)


class FaqAudioService:
    def __init__(self, repository: FaqAudioRepository, entries: FaqRepository,
                 tts: SpeechSynthesizer,
                 cache_dir: str | Path | None = None,
                 quota_mb: int = MAX_CACHE_MB) -> None:
        self._repo = repository
        self._entries = entries
        self._tts = tts
        self._dir = Path(cache_dir) if cache_dir else AUDIO_CACHE_DIR
        self._quota = max(1, int(quota_mb)) * 1024 * 1024
        self._jobs: dict[str, FaqAudioJob] = {}
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------ cache
    def cached(self, entry_id: str, tenant: str, voice: str) -> dict[str, object] | None:
        return self._cached_locked(entry_id, tenant, voice)

    def _cached_locked(self, entry_id: str, tenant: str,
                       voice: str) -> dict[str, object] | None:
        row = self._repo.get_audio(entry_id, tenant, voice)
        if not row:
            return None
        path = Path(str(row["path"]))
        if not path.is_file():
            self._repo.delete_audio(entry_id, tenant, voice)
            return None
        return row

    def _prune_locked(self) -> None:
        """Keep only the most recent job records (they are status only)."""
        if len(self._jobs) <= MAX_JOBS:
            return
        for job in sorted(self._jobs.values(), key=lambda item: item.started_at)[:-MAX_JOBS]:
            self._jobs.pop(job.id, None)

    def usage(self, tenant: str) -> int:
        return self._repo.audio_usage(tenant)

    def resolve_voice(self, voice: str | None = None) -> str | None:
        return self._tts.resolve_voice(voice)

    def reset(self, entry_id: str, tenant: str) -> None:
        self._repo.delete_audio(entry_id, tenant)

    # --------------------------------------------------------------- prerender
    def start(self, entry_id: str, tenant: str, voice: str | None) -> FaqAudioJob:
        entry = self._entries.get(entry_id, tenant)
        if entry is None:
            raise FaqEntryNotFound("không tìm thấy câu hỏi")
        selected = self._tts.resolve_voice(voice)
        if selected is None:
            raise ValueError("chưa chọn được giọng đọc")

        with self._lock:
            existing = self._cached_locked(entry_id, tenant, selected)
            if existing:
                job = FaqAudioJob(id=uuid.uuid4().hex[:12], entry_id=entry_id,
                                  tenant=tenant, voice=selected, status="done",
                                  seconds=float(existing["seconds"]))
                self._jobs[job.id] = job
                self._prune_locked()
                return job
            if self._running:
                raise TtsBusy("đang tổng hợp sẵn một câu khác — thử lại sau")
            job = FaqAudioJob(id=uuid.uuid4().hex[:12], entry_id=entry_id,
                              tenant=tenant, voice=selected)
            self._jobs[job.id] = job
            self._running = True
            self._prune_locked()

        thread = threading.Thread(
            target=self._run, args=(job, entry.answer), daemon=True,
            name=f"faq-audio-{job.id}")
        thread.start()
        return job

    def status(self, job_id: str) -> dict[str, object] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "id": job.id,
            "entry_id": job.entry_id,
            "voice": job.voice,
            "status": job.status,
            "seconds": round(job.seconds, 2),
            "error": job.error,
        }

    def _run(self, job: FaqAudioJob, text: str) -> None:
        prepared = None
        try:
            prepared = self._tts.prepare_stream(text, job.voice)
            for _ in self._tts.stream_job(prepared):
                pass
            if not prepared.finalized:
                raise RuntimeError("tổng hợp không hoàn tất")
            self._dir.mkdir(parents=True, exist_ok=True)
            safe_voice = _VOICE_SAFE.sub("_", job.voice.lower()) or "voice"
            target = self._dir / f"{job.entry_id}__{safe_voice}.wav"
            shutil.copy2(prepared.wav_path, target)
            self._repo.put_audio(
                job.entry_id, job.tenant, voice=job.voice,
                sample_rate=prepared.store.sample_rate,
                path=str(target), seconds=prepared.seconds,
                bytes_=prepared.store.size_bytes,
            )
            job.seconds = prepared.seconds
            job.status = "done"
            self._evict(job.tenant)
        except Exception as exc:  # noqa: BLE001 - reported through job status
            job.status = "error"
            job.error = str(exc) or exc.__class__.__name__
        finally:
            if prepared is not None:
                self._tts.cancel(prepared.id)
            with self._lock:
                self._running = False

    def _evict(self, tenant: str) -> None:
        total = self._repo.audio_usage(tenant)
        if total <= self._quota:
            return
        for row in self._repo.oldest_audio(tenant):
            if total <= self._quota:
                break
            path = Path(str(row["path"]))
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            total -= int(row["bytes"] or 0)
            self._repo.delete_audio(str(row["entry_id"]), tenant,
                                    str(row["voice"]))


__all__ = ["FaqAudioJob", "FaqAudioService", "MAX_CACHE_MB"]
