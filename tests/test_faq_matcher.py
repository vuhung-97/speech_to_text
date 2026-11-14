"""Matcher: lazy embedding, cosine ordering, thresholds, cache invalidation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                                   SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database
from backend.domain.faq.models import FaqEntry


class MapEmbedder:
    """Controllable vectors so thresholds can be tested exactly."""

    model_id = "map"
    version = 1
    dim = 4

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = {key: np.asarray(value, dtype=np.float32)
                        for key, value in mapping.items()}

    def _vector(self, text: str) -> np.ndarray:
        key = text.replace("passage: ", "").replace("query: ", "")
        vector = self.mapping.get(key)
        if vector is None:  # unknown text → orthogonal vector
            vector = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        return vector / np.linalg.norm(vector)

    def embed_documents(self, texts):
        return np.vstack([self._vector(text) for text in texts])

    def embed_query(self, text):
        return self._vector(text)


def make(tmp_path: Path, embedder):
    database = Database(tmp_path / "app.db")
    repo = SqliteFaqRepository(database)
    return repo, SqliteFaqMatcher(repo, embedder)


def add(repo: SqliteFaqRepository, tenant: str, question: str,
        answer: str = "Đáp án.") -> FaqEntry:
    return repo.upsert(FaqEntry(id="", tenant_id=tenant, question=question,
                                answer=answer))


def test_lazy_embedding_and_exact_match(tmp_path: Path) -> None:
    repo, matcher = make(tmp_path, MapEmbedder({
        "Thủ đô Việt Nam là gì?": [1, 0, 0, 0],
        "Thủ đô Việt Nam là gì": [1, 0, 0, 0],
    }))
    entry = add(repo, "local", "Thủ đô Việt Nam là gì?", "Hà Nội.")

    # no embedding yet → matcher embeds it on first use
    result = matcher.match("Thủ đô Việt Nam là gì", "local")
    assert result.matched is not None
    assert result.matched.entry.id == entry.id
    assert result.matched.score == pytest.approx(1.0, abs=1e-5)
    assert result.accepted is True
    assert len(repo.embeddings("local")) == 1


def test_thresholds_decide_status(tmp_path: Path) -> None:
    embedder = MapEmbedder({
        "câu gốc": [1, 0, 0, 0],
        "hỏi gần": [0.8, 0.6, 0, 0],   # cosine 0.8 → near miss
        "hỏi lạc": [0, 1, 0, 0],       # cosine 0.0 → rejected
    })
    repo, matcher = make(tmp_path, embedder)
    matcher.threshold = 0.84
    matcher.near_threshold = 0.78
    add(repo, "local", "câu gốc", "Đáp án.")

    near = matcher.match("hỏi gần", "local")
    assert near.matched is not None
    assert near.near_miss is True
    assert near.accepted is False

    far = matcher.match("hỏi lạc", "local")
    assert far.matched is None
    assert far.candidates and far.candidates[0].entry.question == "câu gốc"


def test_empty_catalogue_and_tenant_isolation(tmp_path: Path) -> None:
    repo, matcher = make(tmp_path, HashingEmbedder())
    assert matcher.match("bất kỳ", "local").matched is None

    add(repo, "acme", "Câu của acme")
    matcher.invalidate("local")
    assert matcher.match("Câu của acme", "local").matched is None
    assert matcher.match("Câu của acme", "acme").matched is not None


def test_cache_refreshes_when_catalogue_changes(tmp_path: Path) -> None:
    repo, matcher = make(tmp_path, MapEmbedder({
        "một": [1, 0, 0, 0],
        "hai": [0, 1, 0, 0],
    }))
    add(repo, "local", "một")
    assert matcher.match("một", "local").matched.entry.question == "một"

    add(repo, "local", "hai", "Đáp án hai.")
    result = matcher.match("hai", "local")
    assert result.matched is not None
    assert result.matched.entry.question == "hai"


def test_candidates_are_ranked(tmp_path: Path) -> None:
    embedder = MapEmbedder({
        "gần nhất": [1, 0, 0, 0],
        "thứ hai": [0.7, 0.7, 0, 0],
        "thứ ba": [0.5, 0.5, 0.7, 0],
    })
    repo, matcher = make(tmp_path, embedder)
    add(repo, "local", "gần nhất", "1")
    add(repo, "local", "thứ hai", "2")
    add(repo, "local", "thứ ba", "3")

    result = matcher.match("gần nhất", "local", k=2)
    names = [item.entry.question for item in result.candidates]
    assert names[:2] == ["thứ hai", "thứ ba"]
