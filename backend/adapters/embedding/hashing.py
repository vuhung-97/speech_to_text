"""Deterministic hashing embedder: the offline fallback with no model file.

Character 3-grams are hashed with CRC32 (stable across processes, unlike
Python's randomised ``hash``) into a fixed-width vector with signed buckets.
It cannot understand paraphrases as well as E5, but it keeps the catalogue
searchable when the ONNX model has not been downloaded, and it is fast enough
to embed a few thousand questions instantly.
"""

from __future__ import annotations

import zlib
from collections.abc import Sequence

import numpy as np

from ...domain.faq.normalize import normalize_question

DIM = 512


class HashingEmbedder:
    """Signed hashing of character n-grams, L2-normalised."""

    model_id = "hashing-char3"
    version = 1
    dim = DIM

    def __init__(self, dim: int = DIM) -> None:
        self.dim = int(dim)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(texts, query=False)

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed([text], query=True)[0]

    def _embed(self, texts: Sequence[str], *, query: bool) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            # Prefixes are an E5 training detail; the hashing fallback compares
            # raw normalised text so an exact question scores a clean 1.0.
            value = normalize_question(text)
            padded = f" {value} "
            for size in (3, 4, 5):
                for start in range(0, max(0, len(padded) - size + 1)):
                    gram = padded[start:start + size]
                    digest = zlib.crc32(gram.encode("utf-8"))
                    index = digest % self.dim
                    sign = 1.0 if (digest >> 16) & 1 else -1.0
                    matrix[row, index] += sign
        return _normalise(matrix)


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


__all__ = ["HashingEmbedder"]
