"""Question normalisation shared by indexing and querying.

Indexing and querying must apply the exact same transformation, otherwise the
same question scores differently depending on which side it came from.
Diacritics are preserved on purpose: Vietnamese embeddings rely on them.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_TRAILING_PUNCT = re.compile(r"[\s\.\,\;\:\!\?…]+$")
_LEADING_PUNCT = re.compile(r"^[\s\.\,\;\:\!\?…]+")


def normalize_question(text: str) -> str:
    """NFC, lowercase, single spaces, no edge punctuation."""
    value = unicodedata.normalize("NFC", (text or "").strip().lower())
    value = _WHITESPACE.sub(" ", value)
    value = _LEADING_PUNCT.sub("", value)
    value = _TRAILING_PUNCT.sub("", value)
    return value


def embed_input(question: str, *, query: bool) -> str:
    """Prefix the text the way E5 models were trained (query vs passage)."""
    prefix = "query: " if query else "passage: "
    return prefix + normalize_question(question)


__all__ = ["embed_input", "normalize_question"]
