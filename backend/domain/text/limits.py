"""Length limits for reading text aloud.

Two entry points exist and they must not drift apart:

- the quick path (``POST /api/tts``) keeps the historical 1000-character cap and
  returns a WAV payload in memory;
- the long-form path (``POST /api/v1/tts/stream``) is capped by **words** (the
  unit the reader thinks in) plus a character ceiling that protects against a
  pathological single token (a URL without spaces) slipping past a word count.

Vietnamese separates syllables with spaces, so ``\\S+`` is an accurate word
counter and is cheap enough to run on every request.
"""

from __future__ import annotations

import re

MAX_TTS_CHARS = 1_000          # quick, in-memory WAV path (unchanged contract)
MAX_TTS_WORDS = 2_000          # long-form path: what the UI shows and enforces
MAX_TTS_STREAM_CHARS = 20_000  # long-form safety net for one huge token

_WORD = re.compile(r"\S+")


class TextTooLong(ValueError):
    """Input exceeds the long-form word or character ceiling (HTTP 413)."""


def word_count(text: str) -> int:
    """Number of whitespace-separated tokens; Vietnamese syllables count as words."""
    return len(_WORD.findall(text or ""))


def check_stream_text(text: str) -> str:
    """Validate long-form input and return it stripped, or raise ``ValueError``."""
    value = (text or "").strip()
    if not value:
        raise ValueError("chưa có văn bản để đọc")
    words = word_count(value)
    if words > MAX_TTS_WORDS:
        raise TextTooLong(
            f"văn bản quá dài ({words} từ, tối đa {MAX_TTS_WORDS} từ)")
    if len(value) > MAX_TTS_STREAM_CHARS:
        raise TextTooLong(
            f"văn bản quá dài ({len(value)} ký tự, tối đa {MAX_TTS_STREAM_CHARS} ký tự)")
    return value


def inspect_stream_text(text: str) -> dict[str, int]:
    """Non-raising variant used by the UI to show counters before submitting."""
    value = (text or "").strip()
    return {
        "chars": len(value),
        "words": word_count(value),
        "max_chars": MAX_TTS_STREAM_CHARS,
        "max_words": MAX_TTS_WORDS,
    }


__all__ = [
    "MAX_TTS_CHARS",
    "MAX_TTS_STREAM_CHARS",
    "MAX_TTS_WORDS",
    "TextTooLong",
    "check_stream_text",
    "inspect_stream_text",
    "word_count",
]
