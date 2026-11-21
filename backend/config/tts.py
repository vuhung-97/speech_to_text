"""Configuration for the optional VieNeu TTS runtime.

Model repository ids, precision folders and environment variables live here so
no service hardcodes them and the SDK boundary is configured in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKBONE_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
CODEC_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"

DEFAULT_PRECISION = "fp32"
PRECISION_SUBFOLDERS = {"fp32": "onnx_update", "int8": "onnx_int8"}
PRECISION_FALLBACK = ("fp32", "int8")

GRAPH_FILES = (
    "vieneu_prefill.onnx",
    "vieneu_decode_step.onnx",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_v3_heads.npz",
    "config.json",
    "tokenizer.json",
)

CODEC_FILES = (
    "moss_audio_tokenizer_decode_full.onnx",
    "moss_audio_tokenizer_decode_shared.data",
    "moss_audio_tokenizer_decode_step.onnx",
    "codec_browser_onnx_meta.json",
    "moss_audio_tokenizer_encode.onnx",
    "moss_audio_tokenizer_encode.data",
)


def requested_precision(explicit: str | None = None) -> str:
    """``VIENEU_PRECISION`` (or the argument) clamped to a known folder."""
    requested = (explicit or os.environ.get("VIENEU_PRECISION") or DEFAULT_PRECISION).lower()
    return requested if requested in PRECISION_SUBFOLDERS else DEFAULT_PRECISION


def requested_threads(explicit: int | None = None) -> int:
    """``VIENEU_THREADS``/argument; ``0`` means "let the SDK decide"."""
    if explicit is not None:
        return int(explicit)
    return int(os.environ.get("VIENEU_THREADS") or 0)


def configure_hub_environment(cache_dir: Path, offline: bool) -> None:
    """Point Hugging Face at the vendored cache before the SDK is imported."""
    if cache_dir.is_dir():
        os.environ["HF_HUB_CACHE"] = str(cache_dir)
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


__all__ = [
    "BACKBONE_REPO",
    "CODEC_FILES",
    "CODEC_REPO",
    "DEFAULT_PRECISION",
    "GRAPH_FILES",
    "PRECISION_FALLBACK",
    "PRECISION_SUBFOLDERS",
    "configure_hub_environment",
    "requested_precision",
    "requested_threads",
]
