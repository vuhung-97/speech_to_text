"""Decide whether a finalized transcript utterance is a question.

Kept deliberately small and pure: the STT pipeline emits finalized text, this
module says "ask this" or "keep dictating", and a later phase wires it to the
QA service. Rules are ordered from strongest signal to weakest.
"""

from __future__ import annotations

import re

# Words that open a Vietnamese question ("ai", "gì", "ở đâu", ...).
_LEADING_MARKERS = (
    "ai", "gì", "nào", "sao", "thế nào", "như thế nào", "ra sao", "làm sao",
    "bao nhiêu", "bao lâu", "bao giờ", "ở đâu", "đâu", "khi nào", "lúc nào",
    "tại sao", "vì sao", "có phải", "có không", "được không", "thế nào là",
    "cho tôi biết", "cho mình hỏi", "hãy cho biết", "xin hỏi", "hỏi",
    "what", "why", "how", "where", "when", "which", "who",
)

# Strong signals that may sit anywhere in the sentence ("... gồm mấy bước nào").
# Bare "gì"/"nào"/"ai" are excluded on purpose: noisy dictation contains them
# inside ordinary statements often enough to make the hint annoying.
_ANYWHERE_MARKERS = (
    "bao nhiêu", "bao lâu", "bao giờ", "ở đâu", "khi nào", "lúc nào",
    "tại sao", "vì sao", "thế nào", "như thế nào", "ra sao", "làm sao",
    "là gì", "là ai", "mấy",
)

# Sentence-final particles that turn a statement into a question.
_TRAILING_PARTICLES = frozenset({
    "không", "chưa", "hả", "à", "ạ", "nhỉ", "chứ", "sao",
    "gì", "nào", "ai", "đâu", "bao nhiêu",
})

_PUNCT = re.compile(r"[\.\,\;\:\!\?…]+$")
_SPACES = re.compile(r"\s+")


def _clean(text: str) -> str:
    value = _SPACES.sub(" ", (text or "").strip().lower())
    return value


def is_question(text: str) -> bool:
    """True when the utterance reads as a question worth asking the catalogue."""
    raw = _clean(text)
    if not raw:
        return False
    if raw.endswith("?"):
        return True

    body = _PUNCT.sub("", raw)
    if not body:
        return False

    for marker in _LEADING_MARKERS:
        if body == marker or body.startswith(marker + " "):
            return True

    for marker in _ANYWHERE_MARKERS:
        if re.search(rf"(?:^|\s){re.escape(marker)}(?:\s|$)", body):
            return True

    last = body.rsplit(" ", 1)[-1]
    return last in _TRAILING_PARTICLES


def merge_continuations(
    parts: list[tuple[str, float]],
    max_gap: float = 1.2,
) -> str:
    """Join consecutive finalized utterances that belong to one question.

    ``parts`` is ``[(text, timestamp_seconds), ...]`` in arrival order. A pause
    longer than ``max_gap`` starts a new question; shorter gaps are treated as
    the speaker continuing the same one.
    """
    if not parts:
        return ""
    merged = [parts[0][0].strip()]
    previous_ts = parts[0][1]
    for text, ts in parts[1:]:
        value = (text or "").strip()
        if not value:
            continue
        if ts - previous_ts > max_gap:
            merged = [value]
        else:
            merged.append(value)
        previous_ts = ts
    return " ".join(part for part in merged if part).strip()


__all__ = ["is_question", "merge_continuations"]
