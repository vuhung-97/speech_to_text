"""Offline Vietnamese text-to-speech via the optional ``vieneu`` SDK.

Public facade: turn text into a WAV payload plus its voice catalog, and run the
long-form streaming job. Model discovery lives in
:mod:`backend.services.tts.engine_loader`, the catalog in
:mod:`backend.services.tts.voice_catalog`, and disk/quota bookkeeping in
:mod:`backend.services.tts.job_store`. HTTP and the UI never touch the SDK.

VieNeu-TTS v3 Turbo is 48 kHz and CPU/ONNX by default. The model files installed
by the VieNeu desktop app are reused from ``models/vieneu/``; the Hugging Face
cache is pointed there so the feature works with no network after install.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from ..config.constants import TTS_SAMPLE_RATE
from ..config.paths import TTS_DISK_QUOTA_MB, TTS_TEMP_DIR, VIENEU_CUSTOM_VOICES, VIENEU_HF_CACHE
from ..config.tts import requested_precision, requested_threads
from ..domain.audio.pcm import silence_pcm, to_pcm16, to_wav_bytes
from ..domain.text.limits import MAX_TTS_CHARS, check_stream_text
from ..domain.text.split import PARAGRAPH_GAP_SEC, split_paragraphs
from .tts.engine_loader import TtsEngineLoader, package_installed
from .tts.errors import (TtsBusy, TtsCancelled, TtsStorageError,
                         TtsUnavailable)
from .tts.job_store import SpeechJob, TtsJobStore
from .tts.voice_catalog import VoiceCatalog

SAMPLE_RATE = TTS_SAMPLE_RATE

logger = logging.getLogger("stt_binh.tts")


class TtsService:
    """Lazy owner of the VieNeu engine, the voice catalog and WAV synthesis."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        custom_voices: Path | str | None = None,
        precision: str | None = None,
        threads: int | None = None,
        temp_root: Path | str | None = None,
        quota_mb: int = TTS_DISK_QUOTA_MB,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else VIENEU_HF_CACHE
        self._custom_voices = Path(custom_voices) if custom_voices else VIENEU_CUSTOM_VOICES
        self._precision = requested_precision(precision)
        self._threads = requested_threads(threads)

        self._catalog = VoiceCatalog(self._custom_voices)
        self._loader = TtsEngineLoader(
            self._cache_dir, self._precision, self._threads,
            self._catalog.read_custom_voices,
        )
        self._engine: Any = None
        self._load_seconds = 0.0
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._store = TtsJobStore(temp_root or TTS_TEMP_DIR, quota_mb)

    # -- availability / catalog -------------------------------------------
    @staticmethod
    def package_installed() -> bool:
        return package_installed()

    def available(self) -> tuple[bool, str]:
        if not self.package_installed():
            return False, "chưa cài package 'vieneu' — chạy: pip install vieneu"
        return True, ""

    def _local_model(self) -> tuple[Path | None, Path | None, bool]:
        return self._loader.local_model()

    def status(self) -> dict[str, Any]:
        ready, reason = self.available()
        _root, onnx_dir, offline = self._local_model() if ready else (None, None, False)
        return {
            "available": ready,
            "reason": reason,
            "local_model": bool(onnx_dir),
            "offline": offline,
            "loaded": self._engine is not None,
            "load_seconds": round(self._load_seconds, 2),
            "sample_rate": SAMPLE_RATE,
            "max_chars": MAX_TTS_CHARS,
            "precision": self._precision,
        }

    def voices(self) -> tuple[list[dict[str, Any]], str]:
        """Return ``(voices, default_id)`` without loading the model."""
        if not self.package_installed():
            return [], ""
        return self._catalog.voices()

    # -- synthesis ---------------------------------------------------------
    def _ensure_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        ready, reason = self.available()
        if not ready:
            raise TtsUnavailable(reason)
        with self._load_lock:
            if self._engine is not None:
                return self._engine
            engine, seconds = self._loader.create()
            self._engine = engine
            self._load_seconds = seconds
            return engine

    def _resolve_voice(self, voice: str | None) -> str | None:
        presets, default = self.voices()
        if voice and voice not in {entry["id"] for entry in presets}:
            raise ValueError(f"giọng '{voice}' không có trong danh sách")
        return voice or default or None

    def resolve_voice(self, voice: str | None = None) -> str | None:
        """Public wrapper used by callers that need the cache key (P6)."""
        return self._resolve_voice(voice)

    @property
    def sample_rate(self) -> int:
        return SAMPLE_RATE

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, float]:
        """Short path: synthesize ``text`` into ``(wav_bytes, audio_seconds)``.

        Bounded by ``MAX_TTS_CHARS`` so holding the result in memory is safe.
        Long text goes through :meth:`synthesize_stream` instead.
        """
        value = (text or "").strip()
        if not value:
            raise ValueError("chưa có văn bản để đọc")
        if len(value) > MAX_TTS_CHARS:
            raise ValueError(f"văn bản quá dài (tối đa {MAX_TTS_CHARS} ký tự)")

        ready, reason = self.available()
        if not ready:
            raise TtsUnavailable(reason)

        selected = self._resolve_voice(voice)
        with self._infer_lock:
            engine = self._ensure_engine()
            try:
                audio = engine.infer(value, voice=selected)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        if audio is None or len(audio) == 0:
            raise ValueError("model không tạo được âm thanh cho văn bản này")
        rate = int(getattr(engine, "sample_rate", SAMPLE_RATE))
        seconds = len(audio) / float(rate)
        return to_wav_bytes(audio, rate), seconds

    def stream_pcm(self, text: str,
                   voice: str | None = None) -> Iterator[bytes]:
        """One-shot streaming entry point required by ``SpeechSynthesizer``."""
        yield from self.synthesize_stream(text, voice)

    def warmup(self, *, synthesize: bool = False) -> bool:
        """Load the TTS engine into RAM ahead of time.

        ``synthesize=True`` also runs one tiny inference so ONNX graph setup and
        voice resolution are paid at startup instead of the first read.
        """
        if not self.package_installed():
            logger.warning("vieneu chưa cài — không nạp trước TTS")
            return False
        if self._engine is not None:
            return True
        try:
            self._ensure_engine()
        except TtsUnavailable as exc:
            logger.warning("không nạp được TTS: %s", exc)
            return False
        logger.info("TTS model đã nạp vào RAM (%.1f giây)", self._load_seconds)
        if synthesize:
            try:
                self.synthesize("Xin chào.", self._resolve_voice(None))
                logger.info("TTS đã chạy thử một câu — sẵn sàng đọc ngay")
            except Exception as exc:  # noqa: BLE001 - warmup must never block startup
                logger.warning("chạy thử TTS thất bại: %s", exc)
        return True

    def preload_async(self, *, synthesize: bool = False) -> threading.Thread:
        thread = threading.Thread(
            target=self.warmup,
            kwargs={"synthesize": synthesize},
            daemon=True,
            name="tts-preload",
        )
        thread.start()
        return thread

    # ------------------------------------------------------- long-form stream
    @property
    def busy(self) -> bool:
        return self._store.busy

    def prepare_stream(
        self, text: str, voice: str | None = None, session_id: str | None = None,
    ) -> SpeechJob:
        """Validate input, reserve disk and create the temp session.

        Called *before* the HTTP response starts, so every rejection (400/409/507)
        is still a normal JSON error instead of a broken audio stream.
        """
        value = check_stream_text(text)
        ready, reason = self.available()
        if not ready:
            raise TtsUnavailable(reason)
        if self._store.busy:
            raise TtsBusy("đang đọc một văn bản khác — dừng lại rồi thử tiếp")
        selected = self._resolve_voice(voice)
        return self._store.create(value, selected, session_id)

    def stream_job(self, job: SpeechJob) -> Iterator[bytes]:
        """Yield PCM16 blocks while writing them to the job's WAV file.

        Memory stays flat: one model block, one PCM block, one socket write.
        Closing the iterator (client disconnect) cancels the job and removes its
        temporary directory.
        """
        if job.started:
            raise RuntimeError("job đã bắt đầu")
        job.started = True
        failed = False
        stream = None
        try:
            with self._infer_lock:
                engine = self._ensure_engine()
                for index, paragraph in enumerate(split_paragraphs(job.text)):
                    if job.cancelled.is_set():
                        break
                    if index:
                        gap = silence_pcm(PARAGRAPH_GAP_SEC, SAMPLE_RATE)
                        job.store.append_pcm(gap)
                        yield gap
                    stream = engine.infer_stream(paragraph, voice=job.voice)
                    try:
                        for block in stream:
                            if job.cancelled.is_set():
                                break
                            pcm = to_pcm16(block)
                            if not pcm:
                                continue
                            job.store.append_pcm(pcm)
                            yield pcm
                    finally:
                        closer = getattr(stream, "close", None)
                        if closer is not None:
                            closer()
                        stream = None
        except GeneratorExit:
            job.cancelled.set()
            raise
        except BaseException as exc:  # noqa: BLE001 - surface the real failure
            failed = True
            job.store.fail(exc)
            raise
        finally:
            self._store.finish(job, failed)

    def synthesize_stream(self, text: str,
                          voice: str | None = None) -> Iterator[bytes]:
        """Convenience: prepare + stream in one call (used by tests and Python)."""
        yield from self.stream_job(self.prepare_stream(text, voice))

    def cancel(self, job_id: str) -> bool:
        return self._store.cancel(job_id)

    def job_status(self, job_id: str) -> dict[str, Any] | None:
        return self._store.status(job_id)

    def job_path(self, job_id: str) -> Path | None:
        return self._store.path(job_id)

    def shutdown(self) -> None:
        """Cancel every job and remove the whole temp tree (called on exit)."""
        self._store.shutdown()


__all__ = [
    "MAX_TTS_CHARS",
    "SpeechJob",
    "TtsBusy",
    "TtsCancelled",
    "TtsService",
    "TtsStorageError",
    "TtsUnavailable",
]
