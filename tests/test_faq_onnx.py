"""Real-model check: the tuned threshold must separate paraphrase from noise.

Skipped unless ``tools/fetch_embed_model.py`` has been run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.onnx_e5 import OnnxE5Embedder
from backend.adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                                   SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database
from backend.domain.faq.models import FaqEntry

pytestmark = pytest.mark.skipif(
    not OnnxE5Embedder.files_present(), reason="models/embed chưa có")


@pytest.fixture()
def matcher(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    repo = SqliteFaqRepository(database)
    embedder = OnnxE5Embedder()
    item = SqliteFaqMatcher(repo, embedder)
    for question, answer in (
        ("Thủ đô Việt Nam là gì?", "Hà Nội."),
        ("Giờ làm việc của văn phòng như thế nào?", "Từ 8h đến 17h."),
        ("Quy trình đăng ký tạm trú gồm mấy bước?", "Ba bước."),
    ):
        repo.upsert(FaqEntry(id="", tenant_id="local", question=question,
                             answer=answer))
    return item


def test_paraphrase_matches(matcher: SqliteFaqMatcher) -> None:
    result = matcher.match("Thủ đô của Việt Nam là gì", "local")
    assert result.matched is not None
    assert result.matched.entry.answer == "Hà Nội."
    assert result.matched.score >= matcher.threshold


def test_off_topic_is_rejected(matcher: SqliteFaqMatcher) -> None:
    for question in ("Thời tiết hôm nay thế nào", "Hôm nay ăn gì",
                     "Mấy giờ rồi", "Giá vàng hôm nay bao nhiêu"):
        result = matcher.match(question, "local")
        assert result.matched is None, (question, result.best_score)
        assert result.candidates


def test_exact_question_scores_highest(matcher: SqliteFaqMatcher) -> None:
    result = matcher.match("Giờ làm việc của văn phòng như thế nào?", "local")
    assert result.matched is not None
    assert result.matched.score > 0.90
