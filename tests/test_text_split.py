"""Speech units: strong punctuation becomes a pause, commas stay inside."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.text.split import (CLAUSE_PAUSE_SEC, LINE_PAUSE_SEC,
                                       PARAGRAPH_PAUSE_SEC, PAREN_PAUSE_SEC,
                                       SENTENCE_PAUSE_SEC, split_speech_units)


def texts(value: str) -> list[str]:
    return [unit.text for unit in split_speech_units(value)]


def pauses(value: str) -> list[float]:
    return [round(unit.pause_after, 2) for unit in split_speech_units(value)]


def test_strong_punctuation_splits_but_comma_does_not() -> None:
    value = "Một, hai; ba: bốn. Năm!"
    assert texts(value) == ["Một, hai;", "ba:", "bốn.", "Năm!"]
    assert pauses(value) == [
        round(CLAUSE_PAUSE_SEC, 2),
        round(CLAUSE_PAUSE_SEC, 2),
        round(SENTENCE_PAUSE_SEC, 2),
        0.0,
    ]


def test_comma_alone_never_creates_a_unit() -> None:
    assert texts("Một, hai, ba.") == ["Một, hai, ba."]


def test_parentheses_become_their_own_units() -> None:
    value = "Trước (nội dung phụ) sau."
    assert texts(value) == ["Trước", "nội dung phụ", "sau."]
    assert pauses(value) == [
        round(PAREN_PAUSE_SEC, 2),
        round(PAREN_PAUSE_SEC, 2),
        0.0,
    ]


def test_decimal_abbreviation_time_and_url_are_not_split() -> None:
    value = "Giá 3.5 triệu, TP.HCM; lúc 12:30."
    assert texts(value) == ["Giá 3.5 triệu, TP.HCM;", "lúc 12:30."]

    assert texts("Mở https://example.com/a:b để xem.") == [
        "Mở https://example.com/a:b để xem."
    ]


def test_ellipsis_is_one_sentence_pause() -> None:
    assert texts("Chờ... rồi.") == ["Chờ...", "rồi."]
    assert pauses("Chờ... rồi.") == [round(SENTENCE_PAUSE_SEC, 2), 0.0]


def test_line_break_and_paragraph_break_have_different_pauses() -> None:
    # A full stop followed by a newline keeps the (longer) sentence pause.
    assert pauses("Một.\nHai.") == [round(SENTENCE_PAUSE_SEC, 2), 0.0]
    # A plain line break (list item without punctuation) gets the line pause.
    assert pauses("Mục một\nMục hai") == [round(LINE_PAUSE_SEC, 2), 0.0]
    assert pauses("Một.\n\nHai.") == [round(PARAGRAPH_PAUSE_SEC, 2), 0.0]


def test_quotes_stay_attached_to_the_sentence() -> None:
    assert texts('Anh nói: "Đi." Rồi.') == ['Anh nói:', '"Đi."', "Rồi."]


def test_punctuation_only_input_produces_no_units() -> None:
    assert texts("... , ()") == []
    assert split_speech_units("   ") == []


def test_tiny_fragment_is_merged_with_the_next_unit() -> None:
    assert texts("A; B.") == ["A; B."]


def test_last_unit_has_no_trailing_pause() -> None:
    assert split_speech_units("Một. Hai!")[-1].pause_after == 0.0
