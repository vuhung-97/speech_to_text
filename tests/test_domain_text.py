"""Domain text rules: the word cap is the UX limit, the char cap is the net."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.text.limits import (MAX_TTS_STREAM_CHARS, MAX_TTS_WORDS,
                                        check_stream_text, inspect_stream_text,
                                        word_count)


def test_word_count_handles_vietnamese_and_whitespace() -> None:
    assert word_count("xin chào bạn") == 3
    assert word_count("  xin\n\nchào\tbạn  ") == 3
    assert word_count("") == 0
    assert word_count("xin chào, bạn!") == 3
    assert word_count("một-hai ba") == 2  # hyphen is part of the token


def test_stream_limit_accepts_exactly_the_cap() -> None:
    text = " ".join(["từ"] * MAX_TTS_WORDS)
    assert check_stream_text(text) == text
    assert inspect_stream_text(text)["words"] == MAX_TTS_WORDS


def test_stream_limit_rejects_one_word_over() -> None:
    text = " ".join(["từ"] * (MAX_TTS_WORDS + 1))
    with pytest.raises(ValueError, match="tối đa 2000 từ"):
        check_stream_text(text)


def test_stream_limit_rejects_one_huge_token() -> None:
    text = "a" * (MAX_TTS_STREAM_CHARS + 1)  # a single "word" slips past counting
    assert word_count(text) == 1
    with pytest.raises(ValueError, match="ký tự"):
        check_stream_text(text)


def test_stream_limit_rejects_empty() -> None:
    for value in ("", "   ", "\n\t"):
        with pytest.raises(ValueError, match="chưa có văn bản"):
            check_stream_text(value)


def test_inspect_reports_counters() -> None:
    info = inspect_stream_text("xin chào")
    assert info == {
        "chars": 8,
        "words": 2,
        "max_chars": MAX_TTS_STREAM_CHARS,
        "max_words": MAX_TTS_WORDS,
    }
