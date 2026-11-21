"""The text actually embedded for a question: the same transform on both sides.

The outline words its questions formally — "Đồng chí hãy trình bày khái niệm
“Tự động hóa chỉ huy”?" — while the user speaks plainly: "tự động hóa chỉ huy
là gì". Embedding the raw strings puts those two far apart, so the catalogue
indexes a *focus* form and every spoken query is reduced the same way before it
is embedded.

One function, one reason to change: the wording rules. It is pure and shared by
the importer (index side) and the matcher (query side), which is what keeps both
sides consistent.
"""

from __future__ import annotations

import re
import unicodedata

from .normalize import normalize_question

_EDGE_PUNCTUATION = re.compile(r"^[\s\"“”«»'’.,;:!?…-]+|[\s\"“”«»'’.,;:!?…-]+$")

# "đồng chí hãy trình bày", "cho biết", and repeats such as "trình bày trình bày".
_LEADING_STYLE = re.compile(
    r"^(?:đồng chí\s+)?(?:hãy\s+)?"
    r"(?:(?:cho biết|nêu|trình bày|phân tích|diễn giải|chứng minh|so sánh|"
    r"đánh giá|giới thiệu|mô tả|làm rõ)\s+)+"
)
# Topic filler that carries no content once the style verb is gone.
_LEADING_TOPIC = re.compile(r"^(?:về|khái niệm|những|vấn đề)\s+")
# Spoken-question tails: "X là gì", "X như thế nào", "X ra sao".
_TRAILING_QUESTION = re.compile(r"[\s,]*(?:là gì|như thế nào|ra sao|như nào)\s*$")
_WHITESPACE = re.compile(r"\s+")

# Bound the rewrite loop: each pass removes at least one prefix, so a handful of
# passes covers every real question and a pathological input cannot spin.
_MAX_PASSES = 6


def _strip_edge_punctuation(value: str) -> str:
    return _EDGE_PUNCTUATION.sub("", value)


def focus_question(text: str) -> str:
    """Return the content-only form of a question, or the normalised original."""
    original = normalize_question(text)
    value = _strip_edge_punctuation(
        unicodedata.normalize("NFC", (text or "").strip().lower()))
    for _ in range(_MAX_PASSES):
        previous = value
        value = _LEADING_STYLE.sub("", value)
        value = _LEADING_TOPIC.sub("", value)
        value = _TRAILING_QUESTION.sub("", value)
        value = _strip_edge_punctuation(value.strip())
        if value == previous:
            break
    return _WHITESPACE.sub(" ", value).strip() or original


__all__ = ["focus_question"]
