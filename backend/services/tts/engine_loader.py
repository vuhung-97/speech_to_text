"""Resolve the VieNeu model on disk and construct the SDK engine.

This module is the only place that imports ``vieneu`` / touches Hugging Face
cache discovery. It is stateless: the facade owns the loaded engine and its
locks, so a test double can replace the engine without patching this file.
"""

from __future__ import annotations

import importlib.util
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

from ...config.tts import (BACKBONE_REPO, CODEC_FILES, CODEC_REPO, GRAPH_FILES,
                           PRECISION_FALLBACK, PRECISION_SUBFOLDERS,
                           configure_hub_environment)
from .errors import TtsUnavailable


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
    candidates = ([path for path in snapshots.iterdir() if path.is_dir()]
                  if snapshots.is_dir() else [])
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _has_files(root: Path | None, names: tuple[str, ...]) -> bool:
    return bool(root) and all((root / name).is_file() for name in names)


def package_installed() -> bool:
    return importlib.util.find_spec("vieneu") is not None


class TtsEngineLoader:
    """Translates configuration into a ready ``Vieneu`` instance."""

    def __init__(
        self,
        cache_dir: Path,
        precision: str,
        threads: int,
        custom_voices: Callable[[], Mapping[str, dict[str, Any]]],
    ) -> None:
        self._cache_dir = cache_dir
        self._precision = precision
        self._threads = threads
        self._custom_voices = custom_voices

    @property
    def precision(self) -> str:
        return self._precision

    def local_model(self) -> tuple[Path | None, Path | None, bool]:
        """Return ``(backbone_root, onnx_dir, offline)`` for the installed cache."""
        root = _snapshot_dir(self._cache_dir, BACKBONE_REPO)
        if root is None:
            return None, None, False
        onnx_dir = root / PRECISION_SUBFOLDERS[self._precision]
        if not _has_files(onnx_dir, GRAPH_FILES):
            for fallback in PRECISION_FALLBACK:
                candidate = root / PRECISION_SUBFOLDERS[fallback]
                if _has_files(candidate, GRAPH_FILES):
                    onnx_dir = candidate
                    break
            else:
                return root, None, False
        codec = _snapshot_dir(self._cache_dir, CODEC_REPO)
        return root, onnx_dir, _has_files(codec, CODEC_FILES)

    def create(self) -> tuple[Any, float]:
        """Load the SDK engine; returns ``(engine, load_seconds)``."""
        root, onnx_dir, offline = self.local_model()
        configure_hub_environment(self._cache_dir, offline)

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
        return engine, time.perf_counter() - started

    def _inject_custom_voices(self, engine: Any) -> None:
        """Merge app-cloned voices into the SDK catalog (built-ins keep precedence)."""
        presets = getattr(engine, "_preset_voices", None)
        if not isinstance(presets, dict):
            return
        for name, entry in self._custom_voices().items():
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


__all__ = ["TtsEngineLoader", "package_installed"]
