"""Split long text into synthesis units without breaking the model's pauses.

The TTS SDK already splits a call into ≤256-character chunks and inserts the
right pause at each boundary. Splitting here on *paragraph* boundaries only —
never on sentences — keeps those pauses intact while giving the UI progress
granularity and the disk writer a natural breath between paragraphs.
"""

from __future__ import annotations

import re

PARAGRAPH_GAP_SEC = 0.35
_MAX_UNIT_CHARS = 4_000

_BLANK_LINE = re.compile(r"\n\s*\n+")


def split_paragraphs(text: str, max_chars: int = _MAX_UNIT_CHARS) -> list[str]:
    """Return non-empty paragraphs, each at most ``max_chars`` characters."""
    value = (text or "").strip()
    if not value:
        return []

    units: list[str] = []
    for raw in _BLANK_LINE.split(value):
        paragraph = raw.strip()
        if not paragraph:
            continue
        units.extend(_hard_split(paragraph, max_chars))
    return units


def _hard_split(paragraph: str, max_chars: int) -> list[str]:
    """Split an oversized paragraph at the last space before ``max_chars``."""
    if len(paragraph) <= max_chars:
        return [paragraph]
    parts: list[str] = []
    remaining = paragraph
    while len(remaining) > max_chars:
        cut = remaining.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return [part for part in parts if part]


__all__ = ["PARAGRAPH_GAP_SEC", "split_paragraphs"]
