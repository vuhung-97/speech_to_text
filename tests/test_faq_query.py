"""Question text normalisation and BM25: the two pure pieces of retrieval."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.faq.lexical import Bm25Index, fold, tokenize
from backend.domain.faq.query import focus_question


@pytest.mark.parametrize("raw,expected", [
    ("Đồng chí hãy trình bày khái niệm “Tự động hóa chỉ huy”?", "tự động hóa chỉ huy"),
    ("đồng chí hãy trình bày về môi trường hoạt động của quy trình C2?",
     "môi trường hoạt động của quy trình c2"),
    ("Trình bày trình bày cấu trúc của trạm vùng?", "cấu trúc của trạm vùng"),
    ("tự động hóa chỉ huy là gì", "tự động hóa chỉ huy"),
    ("mô hình OODA", "mô hình ooda"),
])
def test_focus_question_removes_outline_wording(raw: str, expected: str) -> None:
    assert focus_question(raw) == expected


def test_focus_question_falls_back_to_normalised_text() -> None:
    assert focus_question("  Đồng chí hãy trình bày  ") == "đồng chí hãy trình bày"
    assert focus_question("") == ""


def test_fold_and_tokenize_drop_diacritics_and_stopwords() -> None:
    assert fold("TĐHCH C2") == "tdhch c2"
    assert tokenize("Cấu trúc của trạm vùng là gì") == ["cau", "truc", "tram", "vung"]


def test_bm25_prefers_the_document_with_the_matching_token() -> None:
    index = Bm25Index(["cấu trúc trạm chính", "cấu trúc trạm vùng"])

    scores = index.scores("cấu trúc trạm vùng")
    assert scores[1] > scores[0] > 0

    assert index.scores("thời tiết hôm nay").tolist() == [0.0, 0.0]
    assert index.scores("").tolist() == [0.0, 0.0]
