"""Offline Vietnamese text-to-speech via the optional ``vieneu`` SDK.

One responsibility: turn text into a WAV payload plus its voice catalog. Model
loading, local-cache discovery and serialisation live here; HTTP and the UI never
touch the SDK directly.

VieNeu-TTS v3 Turbo is 48 kHz and CPU/ONNX by default. The model files installed
by the VieNeu desktop app are reused from ``models/vieneu/``; the Hugging Face
cache is pointed there so the feature works with no network after install.
"""

from __future__ import annotations

import importlib.util
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from ..config.paths import (TTS_DISK_QUOTA_MB, TTS_TEMP_DIR, VIENEU_CUSTOM_VOICES,
                            VIENEU_HF_CACHE)
from ..domain.audio.pcm import silence_pcm, to_pcm16, to_wav_bytes
from ..domain.text.limits import check_stream_text
from ..domain.text.split import PARAGRAPH_GAP_SEC, split_paragraphs
from .audio.temp_store import (TempAudioStore, TempSession, cleanup_stale_sessions,
                               free_bytes)

MAX_TTS_CHARS = 1000
SAMPLE_RATE = 48_000
BACKBONE_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
CODEC_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
_PRECISION_SUBFOLDERS = {"fp32": "onnx_update", "int8": "onnx_int8"}
_PRECISION_FALLBACK = ("fp32", "int8")

_GRAPH_FILES = (
    "vieneu_prefill.onnx",
    "vieneu_decode_step.onnx",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_v3_heads.npz",
    "config.json",
    "tokenizer.json",
)
_CODEC_FILES = (
    "moss_audio_tokenizer_decode_full.onnx",
    "moss_audio_tokenizer_decode_shared.data",
    "moss_audio_tokenizer_decode_step.onnx",
    "codec_browser_onnx_meta.json",
    "moss_audio_tokenizer_encode.onnx",
    "moss_audio_tokenizer_encode.data",
)


class TtsUnavailable(RuntimeError):
    """The optional TTS runtime or its model files are not installed."""


class TtsBusy(RuntimeError):
    """A long-form synthesis is already running (one at a time by design)."""


class TtsStorageError(RuntimeError):
    """Not enough free disk space for the requested audio."""


class TtsCancelled(RuntimeError):
    """The client cancelled a synthesis job."""


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


def _repo_dir(cache: Path, repo_id: str) -> Path:
    return cache / f"models--{repo_id.replace('/', '--')}"


def _snapshot_dir(cache: Path, repo_id: str) -> Path | None:
    """Resolve the snapshot referenced by ``refs/main`` (else the newest one)."""
    base = _repo_dir(cache, repo_id)
    if not base.is_dir():
        return None
    snapshots = base / "snapshots"
    ref = base / "refs" / "main"
    if ref.is_file():
        pinned = snapshots / ref.read_text(encoding="utf-8").strip()
        if pinned.is_dir():
            return pinned
    candidates = [path for path in snapshots.iterdir() if path.is_dir()] if snapshots.is_dir() else []
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _has_files(root: Path | None, names: tuple[str, ...]) -> bool:
    return bool(root) and all((root / name).is_file() for name in names)


def _to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    """Mono float32 in [-1, 1] -> a self-contained PCM16 WAV payload.

    Converted block by block so the peak stays ~2.5× the waveform instead of
    the ~5× of clip/copy/tobytes/getvalue chaining.
    """
    return to_wav_bytes(audio, sample_rate)


def _voice_label(name: str, entry: dict[str, Any]) -> str:
    description = str(entry.get("description") or "").strip()
    label = f"{name} — {description}" if description else name
    return f"⭐ {label}" if entry.get("featured") else label


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
        requested = (precision or os.environ.get("VIENEU_PRECISION") or "fp32").lower()
        self._precision = requested if requested in _PRECISION_SUBFOLDERS else "fp32"
        env_threads = os.environ.get("VIENEU_THREADS")
        self._threads = int(threads if threads is not None else (env_threads or 0))
        self._engine: Any = None
        self._load_seconds = 0.0
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

        # long-form streaming state
        self._temp_root = Path(temp_root) if temp_root else TTS_TEMP_DIR
        self._quota_bytes = max(1, int(quota_mb)) * 1024 * 1024
        self._bytes_per_second = SAMPLE_RATE * 2
        self._jobs: dict[str, SpeechJob] = {}
        self._jobs_lock = threading.Lock()
        self._active: SpeechJob | None = None

    # -- availability / catalog -------------------------------------------
    @staticmethod
    def package_installed() -> bool:
        return importlib.util.find_spec("vieneu") is not None

    def available(self) -> tuple[bool, str]:
        if not self.package_installed():
            return False, "chưa cài package 'vieneu' — chạy: pip install vieneu"
        return True, ""

    def _local_model(self) -> tuple[Path | None, Path | None, bool]:
        """Return ``(backbone_root, onnx_dir, offline)`` for the installed cache."""
        root = _snapshot_dir(self._cache_dir, BACKBONE_REPO)
        if root is None:
            return None, None, False
        onnx_dir = root / _PRECISION_SUBFOLDERS[self._precision]
        if not _has_files(onnx_dir, _GRAPH_FILES):
            for fallback in _PRECISION_FALLBACK:
                candidate = root / _PRECISION_SUBFOLDERS[fallback]
                if _has_files(candidate, _GRAPH_FILES):
                    onnx_dir = candidate
                    break
            else:
                return root, None, False
        codec = _snapshot_dir(self._cache_dir, CODEC_REPO)
        return root, onnx_dir, _has_files(codec, _CODEC_FILES)

    def status(self) -> dict[str, Any]:
        ready, reason = self.available()
        root, onnx_dir, offline = self._local_model() if ready else (None, None, False)
        return {
            "available": ready,
            "reason": reason,
            "local_model": _has_files(onnx_dir, _GRAPH_FILES),
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
        presets, default = self._read_presets()
        entries: list[dict[str, Any]] = []
        custom = self._read_custom_voices()

        ordered = sorted(
            presets.items(),
            key=lambda item: (item[1].get("featured") is None, item[1].get("featured") or 0),
        )
        for name, entry in ordered:
            entries.append({
                "id": name,
                "label": _voice_label(name, entry),
                "gender": str(entry.get("gender") or ""),
                "featured": bool(entry.get("featured")),
                "custom": False,
            })
        for name, entry in custom.items():
            entries.append({
                "id": name,
                "label": _voice_label(name, entry),
                "gender": str(entry.get("gender") or ""),
                "featured": False,
                "custom": True,
            })
        if not default:
            default = entries[0]["id"] if entries else ""
        return entries, default

    def _read_presets(self) -> tuple[dict[str, Any], str]:
        spec = importlib.util.find_spec("vieneu")
        if spec is None or not spec.origin:
            return {}, ""
        path = Path(spec.origin).parent / "assets" / "voices_v3_turbo.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}, ""
        presets = data.get("presets")
        return (presets if isinstance(presets, dict) else {}), str(data.get("default_voice") or "")

    def _read_custom_voices(self) -> dict[str, dict[str, Any]]:
        """Cloned voices saved by the VieNeu desktop app (speaker embedding + codes)."""
        try:
            data = json.loads(self._custom_voices.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        voices = data.get("voices")
        if not isinstance(voices, dict):
            return {}
        return {
            name: entry
            for name, entry in voices.items()
            if isinstance(entry, dict) and entry.get("speaker_emb")
        }

    # -- synthesis ---------------------------------------------------------
    def _prepare_environment(self, offline: bool) -> None:
        # Must run before ``vieneu``/``huggingface_hub`` are imported: the hub reads
        # its cache location at import time.
        if self._cache_dir.is_dir():
            os.environ["HF_HUB_CACHE"] = str(self._cache_dir)
        if offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    def _ensure_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        ready, reason = self.available()
        if not ready:
            raise TtsUnavailable(reason)
        with self._load_lock:
            if self._engine is not None:
                return self._engine
            root, onnx_dir, offline = self._local_model()
            self._prepare_environment(offline)

            from vieneu import Vieneu

            started = time.perf_counter()
            kwargs: dict[str, Any] = {
                "backend": "onnx",
                "precision": self._precision,
                "threads": self._threads,
            }
            if root is not None and onnx_dir is not None:
                kwargs.update(backbone_repo=str(root), onnx_dir=str(onnx_dir))
            else:
                kwargs["backbone_repo"] = BACKBONE_REPO
            try:
                engine = Vieneu(**kwargs)
            except Exception as exc:  # missing/incomplete model, hub offline, bad ONNX…
                raise TtsUnavailable(f"không nạp được model TTS: {exc}") from exc
            self._inject_custom_voices(engine)
            self._engine = engine
            self._load_seconds = time.perf_counter() - started
            return engine

    def _inject_custom_voices(self, engine: Any) -> None:
        """Merge app-cloned voices into the SDK catalog (built-ins keep precedence)."""
        presets = getattr(engine, "_preset_voices", None)
        if not isinstance(presets, dict):
            return
        for name, entry in self._read_custom_voices().items():
            embedding = entry.get("speaker_emb") if isinstance(entry, dict) else None
            if not embedding or name in presets:
                continue
            codes = entry.get("codes")
            presets[name] = {
                "description": str(entry.get("description") or "giọng clone"),
                "gender": str(entry.get("gender") or ""),
                "style": "tu_nhien",
                "featured": None,
                "aliases": [],
                "speaker_emb": np.asarray(embedding, dtype=np.float32),
                "codes": np.asarray(codes, dtype=np.int64) if codes else None,
            }

    def _resolve_voice(self, voice: str | None) -> str | None:
        presets, default = self.voices()
        if voice and voice not in {entry["id"] for entry in presets}:
            raise ValueError(f"giọng '{voice}' không có trong danh sách")
        return voice or default or None

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
        return _to_wav(audio, rate), seconds

    # ------------------------------------------------------- long-form stream
    @property
    def busy(self) -> bool:
        active = self._active
        return bool(active and not active.finalized and not active.cancelled.is_set())

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
        if self.busy:
            raise TtsBusy("đang đọc một văn bản khác — dừng lại rồi thử tiếp")
        selected = self._resolve_voice(voice)

        estimated = max(1.0, len(value) / 11.7)  # ~11.7 chars/second of speech
        needed = int(estimated * self._bytes_per_second)
        if needed > self._quota_bytes:
            raise TtsStorageError(
                "văn bản vượt quá hạn mức đĩa cho phép — giảm bớt độ dài")
        self._evict_for_quota(needed)
        if free_bytes(self._temp_root) < needed + 64 * 1024 * 1024:
            raise TtsStorageError(
                "không đủ dung lượng đĩa cho văn bản này — giảm bớt độ dài")

        session = TempSession(self._temp_root, session_id)
        store = session.store("audio", SAMPLE_RATE)
        job = SpeechJob(
            id=session.id,
            session=session,
            store=store,
            text=value,
            voice=selected,
            estimated_seconds=estimated,
        )
        with self._jobs_lock:
            self._jobs[job.id] = job
            self._active = job
        return job

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
            with self._jobs_lock:
                if self._active is job:
                    self._active = None
            if failed or job.cancelled.is_set():
                self._drop_job(job)
            elif not job.finalized:
                job.store.finalize()
                job.finalized = True

    def synthesize_stream(self, text: str,
                          voice: str | None = None) -> Iterator[bytes]:
        """Convenience: prepare + stream in one call (used by tests and Python)."""
        yield from self.stream_job(self.prepare_stream(text, voice))

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.cancelled.set()
        job.store.fail(TtsCancelled("đã huỷ"))
        if job.finalized:
            self._drop_job(job)
        return True

    def job_status(self, job_id: str) -> dict[str, Any] | None:
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
            "sample_rate": SAMPLE_RATE,
            "finalized": job.finalized,
            "cancelled": job.cancelled.is_set(),
            "progress": round(min(1.0, done / estimate), 3),
        }

    def job_path(self, job_id: str) -> Path | None:
        job = self._jobs.get(job_id)
        if job is None or not job.finalized:
            return None
        return job.wav_path

    def shutdown(self) -> None:
        """Cancel every job and remove the whole temp tree (called on exit)."""
        with self._jobs_lock:
            jobs = list(self._jobs.values())
            self._jobs.clear()
            self._active = None
        for job in jobs:
            job.cancelled.set()
            job.session.cleanup()
        cleanup_stale_sessions(self._temp_root, max_age_hours=0)

    # ------------------------------------------------------------------ quota
    def _drop_job(self, job: SpeechJob) -> None:
        with self._jobs_lock:
            self._jobs.pop(job.id, None)
            if self._active is job:
                self._active = None
        job.session.cleanup()

    def _evict_for_quota(self, needed: int) -> None:
        """Delete the oldest finished jobs until ``needed`` bytes fit the quota."""
        with self._jobs_lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at)
        total = sum(job.bytes for job in jobs)
        for job in jobs:
            if total + needed <= self._quota_bytes:
                break
            if job is self._active or not job.finalized:
                continue
            total -= job.bytes
            self._drop_job(job)


__all__ = [
    "MAX_TTS_CHARS",
    "SpeechJob",
    "TtsBusy",
    "TtsCancelled",
    "TtsService",
    "TtsStorageError",
    "TtsUnavailable",
]
