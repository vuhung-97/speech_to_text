"""Catalogue input rules: what the operator may save.

Question cap keeps the embedding focused; answer cap is the same 2000-word
reading limit the TTS path enforces, so a saved answer is always readable.
"""

from __future__ import annotations

from ..text.limits import MAX_TTS_WORDS, word_count

MAX_FAQ_QUESTION_CHARS = 500
MAX_FAQ_CATEGORY_CHARS = 60
DUPLICATE_THRESHOLD = 0.97


def validate_entry(question: str, answer: str,
                   category: str = "") -> tuple[str, str, str]:
    """Return ``(question, answer, category)`` cleaned, or raise ValueError."""
    clean_question = " ".join((question or "").split())
    clean_answer = (answer or "").strip()
    clean_category = " ".join((category or "").split())[:MAX_FAQ_CATEGORY_CHARS]

    if not clean_question:
        raise ValueError("câu hỏi không được để trống")
    if not clean_answer:
        raise ValueError("câu trả lời không được để trống")
    if len(clean_question) > MAX_FAQ_QUESTION_CHARS:
        raise ValueError(
            f"câu hỏi quá dài (tối đa {MAX_FAQ_QUESTION_CHARS} ký tự)")
    words = word_count(clean_answer)
    if words > MAX_TTS_WORDS:
        raise ValueError(
            f"câu trả lời quá dài ({words} từ, tối đa {MAX_TTS_WORDS} từ)")
    return clean_question, clean_answer, clean_category


__all__ = [
    "DUPLICATE_THRESHOLD",
    "MAX_FAQ_CATEGORY_CHARS",
    "MAX_FAQ_QUESTION_CHARS",
    "validate_entry",
]
