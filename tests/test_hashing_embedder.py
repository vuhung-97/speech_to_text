"""Hashing embedder: deterministic, normalised, no model file needed."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder


def test_shape_and_normalisation() -> None:
    embedder = HashingEmbedder()
    matrix = embedder.embed_documents(["xin chào", "quy trình đăng ký"])
    assert matrix.shape == (2, embedder.dim)
    assert matrix.dtype == np.float32
    assert np.allclose(np.linalg.norm(matrix, axis=1), 1.0, atol=1e-5)


def test_deterministic_across_instances() -> None:
    first = HashingEmbedder().embed_query("Thủ đô Việt Nam là gì?")
    second = HashingEmbedder().embed_query("Thủ đô Việt Nam là gì?")
    assert np.allclose(first, second)


def test_query_and_document_match_exactly() -> None:
    embedder = HashingEmbedder()
    query = embedder.embed_query("thủ đô")
    passage = embedder.embed_documents(["thủ đô"])[0]
    assert np.allclose(query, passage)


def test_related_text_scores_higher_than_unrelated() -> None:
    embedder = HashingEmbedder()
    base = embedder.embed_documents(["thủ đô việt nam là gì"])[0]
    related = embedder.embed_query("thủ đô của việt nam là gì")
    unrelated = embedder.embed_query("giờ làm việc của văn phòng")

    assert float(base @ related) > float(base @ unrelated)
    assert float(base @ related) > 0.6


def test_empty_text_is_safe() -> None:
    embedder = HashingEmbedder()
    vector = embedder.embed_query("")
    assert vector.shape == (embedder.dim,)
    assert np.isfinite(vector).all()
