"""Split text into speech units with explicit pauses at strong punctuation.

Why this exists: VieNeu packs every sentence of a paragraph shorter than ~256
characters into **one** model chunk and only inserts silence at chunk
boundaries. Inside a chunk the model has to invent the pauses, and its
normalizer folds ``; :`` into commas and drops brackets — so punctuation was
audible but barely separated. We therefore pre-split at strong punctuation and
insert the pause ourselves.

Commas are deliberately **not** boundaries: keeping them inside a unit lets the
model keep its natural comma prosody instead of producing a sentence-final
cadence at every clause.
"""

from __future__ import annotations

from dataclasses import dataclass

SENTENCE_PAUSE_SEC = 0.35   # . ! ? …
CLAUSE_PAUSE_SEC = 0.22     # ; :
PAREN_PAUSE_SEC = 0.18      # ( )
LINE_PAUSE_SEC = 0.30       # single newline
PARAGRAPH_PAUSE_SEC = 0.60  # blank line

_MAX_UNIT_CHARS = 4_000
# Units shorter than this are punctuation noise / one-letter fragments; merge
# them into the next unit so the model does not synthesize a tiny chunk alone.
_MIN_UNIT_CHARS = 3

_SENTENCE_CHARS = frozenset(".!?…")
# Closing characters that belong to the sentence they follow.
_TRAILING = "\"'”’)]},;:"
_TRAILING_CLAUSE = "\"'”’)]}"


@dataclass(frozen=True)
class SpeechUnit:
    """One synthesis unit and the silence the app inserts after it."""

    text: str
    pause_after: float = 0.0


def split_speech_units(text: str,
                       max_chars: int = _MAX_UNIT_CHARS) -> list[SpeechUnit]:
    """Return ordered units; each carries the pause to insert after it."""
    value = (text or "").strip()
    if not value:
        return []

    units = _merge_tiny(_scan(value))
    units = _hard_split(units, max_chars)
    if units:
        # Never add trailing silence at the end of the document.
        units[-1] = SpeechUnit(units[-1].text, 0.0)
    return units


# --------------------------------------------------------------------------
# Scanner
# --------------------------------------------------------------------------
def _scan(text: str) -> list[SpeechUnit]:
    units: list[SpeechUnit] = []
    buffer: list[str] = []
    index = 0
    length = len(text)

    def emit(pause: float) -> None:
        raw = "".join(buffer).strip()
        buffer.clear()
        if _has_speech(raw):
            units.append(SpeechUnit(raw, pause))
        elif units:
            # Consecutive punctuation / whitespace: strengthen the previous
            # boundary instead of creating an empty unit.
            units[-1] = SpeechUnit(
                units[-1].text, max(units[-1].pause_after, pause))

    while index < length:
        char = text[index]

        if char == "(":
            emit(PAREN_PAUSE_SEC)
            index, inner = _consume_parenthetical(text, index)
            if inner:
                inner_units = _scan(inner)
                units.extend(inner_units)
                if units:
                    last = units[-1]
                    units[-1] = SpeechUnit(
                        last.text, max(last.pause_after, PAREN_PAUSE_SEC))
            continue

        if char == ")":
            index += 1  # unmatched closing bracket: drop it
            continue

        if char in "\r\n":
            start = index
            newlines = 0
            while index < length and text[index] in "\r\n":
                if text[index] == "\n":
                    newlines += 1
                index += 1
            pause = PARAGRAPH_PAUSE_SEC if newlines >= 2 else LINE_PAUSE_SEC
            if not "".join(buffer).strip() and units:
                last = units[-1]
                units[-1] = SpeechUnit(
                    last.text, max(last.pause_after, pause))
            else:
                emit(pause)
            if index == start:
                index += 1
            continue

        if char in _SENTENCE_CHARS:
            if char == "." and not _is_sentence_dot(text, index):
                buffer.append(char)
                index += 1
                continue

            end = index + 1
            while end < length and text[end] in _SENTENCE_CHARS:
                end += 1
            while end < length and text[end] in _TRAILING:
                end += 1
            buffer.append(text[index:end])
            emit(SENTENCE_PAUSE_SEC)
            index = end
            continue

        if char in ";:":
            if not _is_clause_mark(text, index):
                buffer.append(char)
                index += 1
                continue

            end = index + 1
            while end < length and text[end] in ";:":
                end += 1
            while end < length and text[end] in _TRAILING_CLAUSE:
                end += 1
            buffer.append(text[index:end])
            emit(CLAUSE_PAUSE_SEC)
            index = end
            continue

        buffer.append(char)
        index += 1

    emit(0.0)
    return units


def _consume_parenthetical(text: str, start: int) -> tuple[int, str]:
    """Collect the content of ``( ... )`` and return ``(next_index, content)``."""
    depth = 0
    index = start
    inner: list[str] = []
    while index < len(text):
        char = text[index]
        if char == "(":
            depth += 1
            if depth > 1:
                inner.append(" ")
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1, "".join(inner).strip()
            inner.append(" ")
        else:
            inner.append(char)
        index += 1
    return index, "".join(inner).strip()


def _is_sentence_dot(text: str, index: int) -> bool:
    """True only when this ``.`` really ends a sentence."""
    previous = text[index - 1] if index > 0 else ""
    following = text[index + 1] if index + 1 < len(text) else ""

    if previous.isdigit() and following.isdigit():
        return False  # 3.5, 12.11.2026
    if following and (following.isalnum() or following in "_/"):
        return False  # TP.HCM, https://example.com
    return True


def _is_clause_mark(text: str, index: int) -> bool:
    """True only when ``;`` / ``:`` really separates clauses."""
    if text[index] == ";":
        return True  # a semicolon is a strong separator in prose

    previous = text[index - 1] if index > 0 else ""
    following = text[index + 1] if index + 1 < len(text) else ""

    if previous.isdigit() and following.isdigit():
        return False  # 12:30
    if following == "/":
        return False  # https://
    if following and following.isalnum() and not following.isspace():
        return False  # token such as A:B
    return True


def _has_speech(value: str) -> bool:
    return any(char.isalnum() for char in value)


# --------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------
def _merge_tiny(units: list[SpeechUnit]) -> list[SpeechUnit]:
    merged: list[SpeechUnit] = []
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        if merged and len(merged[-1].text) < _MIN_UNIT_CHARS:
            previous = merged.pop()
            merged.append(SpeechUnit(
                f"{previous.text} {text}", unit.pause_after))
        else:
            merged.append(SpeechUnit(text, unit.pause_after))

    if len(merged) >= 2 and len(merged[-1].text) < _MIN_UNIT_CHARS:
        last = merged.pop()
        previous = merged.pop()
        merged.append(SpeechUnit(
            f"{previous.text} {last.text}",
            max(previous.pause_after, last.pause_after)))
    return merged


def _hard_split(units: list[SpeechUnit],
                max_chars: int) -> list[SpeechUnit]:
    """Split an over-long unit at spaces, keeping the pause on its last part."""
    if max_chars <= 0:
        return units

    result: list[SpeechUnit] = []
    for unit in units:
        if len(unit.text) <= max_chars:
            result.append(unit)
            continue
        parts = _split_long(unit.text, max_chars)
        for position, part in enumerate(parts):
            pause = unit.pause_after if position == len(parts) - 1 else 0.0
            result.append(SpeechUnit(part, pause))
    return result


def _split_long(paragraph: str, max_chars: int) -> list[str]:
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


__all__ = [
    "CLAUSE_PAUSE_SEC",
    "LINE_PAUSE_SEC",
    "PARAGRAPH_PAUSE_SEC",
    "PAREN_PAUSE_SEC",
    "SENTENCE_PAUSE_SEC",
    "SpeechUnit",
    "split_speech_units",
]
