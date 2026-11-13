"""Embedding contract: text in, L2-normalised float32 matrix out."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Swap-friendly embedding backend (ONNX E5 today, anything later)."""

    model_id: str
    version: int
    dim: int

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """``(n, dim)`` float32, each row unit length, ready for cosine via dot."""
        ...

    def embed_query(self, text: str) -> np.ndarray:
        """``(dim,)`` float32, unit length."""
        ...


__all__ = ["Embedder"]
