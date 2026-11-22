"""Read a question/answer outline (``.docx``) into importable pairs.

The shape units hand out is stable: a ``Câu I.1.1`` heading, then a two-column
table whose first row is the question (points on the right), then ``Đáp án``,
then one answer paragraph per row with its point value on the right. This
module reads that shape with the standard library only (``zipfile`` +
``xml.etree``) — no Word dependency — and tolerates the usual export quirks:

- tables wrapped in content controls (``w:sdt``), merged/empty cells;
- question text on the heading line (``Câu 3: …``) or spread over rows;
- a missing ``Đáp án`` heading, or point cells in either column;
- a document without tables, where paragraphs carry the same structure.

It returns :class:`FaqOutline` value objects only. Deciding what is valid,
duplicated or new stays in :class:`backend.services.faq_service.FaqService`.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterator
from xml.etree import ElementTree

from ...config.constants import BYTES_PER_MB
from ...domain.faq.models import FaqOutline

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCUMENT_PART = "word/document.xml"
MAX_DOCUMENT_BYTES = 64 * BYTES_PER_MB

# "Câu I.1.1", "Câu 12", "Câu 2.3", "Câu II-4-11" — the trailing text is the
# question when the author wrote it on the heading line.
_QUESTION_CODE = re.compile(
    r"^câu\s+([ivxlcdm]+|\d+)((?:[.\-]\d+){0,3})\s*[.:)\-]?\s*(.*)$",
    re.IGNORECASE,
)
_POINT_CELL = re.compile(r"^\d+(?:[.,]\d+)?\s*(?:đ|điểm)\.?$", re.IGNORECASE)
_ANSWER_HEADING = re.compile(r"^đáp\s*án\s*[:.]?$", re.IGNORECASE)
_WHITESPACE = re.compile(r"[ \t\u00a0]+")
_BLANK_LINES = re.compile(r"\n{3,}")


class DocxFormatError(ValueError):
    """The upload is not a readable ``.docx`` outline."""


def parse_docx(data: bytes) -> list[FaqOutline]:
    """Return every complete pair in document order, or raise ``DocxFormatError``."""
    root = _read_document(data)
    body = root.find(f"{_W}body")
    if body is None:
        raise DocxFormatError("tệp .docx thiếu phần nội dung (w:body)")

    blocks = list(_iter_blocks(body))
    entries = _entries_from_tables(blocks)
    if not entries and not any(kind == "table" for kind, _ in blocks):
        entries = _entries_from_paragraphs(blocks)
    if not entries:
        raise DocxFormatError(
            "không đọc được câu hỏi/đáp án nào — mỗi câu cần dòng «Câu …» và "
            "bảng hoặc đoạn «Đáp án» ngay sau đó")
    return entries


# --------------------------------------------------------------------- reading
def _read_document(data: bytes) -> ElementTree.Element:
    if not data:
        raise DocxFormatError("tệp rỗng")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise DocxFormatError(
            "tệp không phải .docx hợp lệ (nếu là .doc, hãy lưu lại dạng .docx)") from exc
    try:
        info = archive.getinfo(DOCUMENT_PART)
    except KeyError as exc:
        raise DocxFormatError("tệp .docx thiếu word/document.xml") from exc
    if info.file_size > MAX_DOCUMENT_BYTES:
        raise DocxFormatError("nội dung .docx quá lớn để đọc")
    try:
        return ElementTree.fromstring(archive.read(info))
    except ElementTree.ParseError as exc:
        raise DocxFormatError("không đọc được nội dung XML của tệp .docx") from exc


def _iter_blocks(container: ElementTree.Element) -> Iterator[tuple[str, object]]:
    """Yield ``("paragraph", text)`` / ``("table", rows)`` in document order."""
    for child in container:
        if child.tag == f"{_W}sdt":
            content = child.find(f"{_W}sdtContent")
            if content is not None:
                yield from _iter_blocks(content)
        elif child.tag == f"{_W}p":
            yield "paragraph", _paragraph_text(child)
        elif child.tag == f"{_W}tbl":
            yield "table", _table_rows(child)


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag == f"{_W}tab":
            parts.append(" ")
        elif node.tag == f"{_W}br":
            parts.append("\n")
    return _clean("".join(parts))


def _table_rows(table: ElementTree.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall(f"{_W}tr"):
        cells = [_cell_text(cell) for cell in row.findall(f"{_W}tc")]
        if any(cells):
            rows.append(cells)
    return rows


def _cell_text(cell: ElementTree.Element) -> str:
    paragraphs = [_paragraph_text(paragraph)
                  for paragraph in cell.findall(f"{_W}p")]
    return "\n".join(text for text in paragraphs if text)


def _clean(text: str) -> str:
    value = _WHITESPACE.sub(" ", text.replace("\u00a0", " "))
    value = "\n".join(line.strip() for line in value.split("\n"))
    return _BLANK_LINES.sub("\n\n", value).strip()


# --------------------------------------------------------------------- parsing
def _match_heading(text: str) -> tuple[str, str, str] | None:
    """Return ``(code, category, inline_question)`` for a «Câu …» line."""
    match = _QUESTION_CODE.match(text.strip())
    if match is None:
        return None
    base, tail, remainder = match.group(1), match.group(2), match.group(3)
    parts = [base] + [piece for piece in re.split(r"[.\-]", tail) if piece]
    category = ".".join(parts[:-1])
    label = base.upper() if not base.isdigit() else base
    code = f"Câu {label}{tail}".strip()
    return code, category, remainder.strip()


def _is_answer_heading(cell: str) -> bool:
    return bool(_ANSWER_HEADING.match(cell.strip()))


def _is_point_cell(cell: str) -> bool:
    return bool(_POINT_CELL.match(cell.strip()))


def _entries_from_tables(
    blocks: list[tuple[str, object]],
) -> list[FaqOutline]:
    entries: list[FaqOutline] = []
    code = ""
    category = ""
    inline_question = ""
    for kind, payload in blocks:
        if kind == "paragraph":
            heading = _match_heading(str(payload))
            if heading is None:
                continue
            code, category, inline_question = heading
            continue

        rows = payload
        if not isinstance(rows, list) or not rows:
            continue
        entry = _entry_from_rows(rows, code, category, inline_question)
        if entry is not None:
            entries.append(entry)
        code, category, inline_question = "", "", ""
    return entries


def _entry_from_rows(rows: list[list[str]], code: str, category: str,
                     inline_question: str) -> FaqOutline | None:
    heading_index = next(
        (index for index, row in enumerate(rows) if row and _is_answer_heading(row[0])),
        None,
    )
    if heading_index is None:
        question_rows, answer_rows = rows[:1], rows[1:]
    else:
        question_rows, answer_rows = rows[:heading_index], rows[heading_index + 1:]

    question_parts = [row[0] for row in question_rows
                      if row and row[0] and not _is_point_cell(row[0])]
    answer_parts = [row[0] for row in answer_rows
                    if row and row[0] and not _is_point_cell(row[0])
                    and not _is_answer_heading(row[0])]

    question = " ".join([*question_parts, inline_question]).strip()
    answer = "\n".join(answer_parts).strip()
    if not question or not answer:
        return None
    return FaqOutline(code=code, category=category, question=question,
                      answer=answer)


def _entries_from_paragraphs(
    blocks: list[tuple[str, object]],
) -> list[FaqOutline]:
    """Fallback for documents that write answers as paragraphs, not tables."""
    entries: list[FaqOutline] = []
    code = ""
    category = ""
    question: list[str] = []
    answer: list[str] = []
    in_answer = False

    def flush() -> None:
        if question and answer:
            entries.append(FaqOutline(
                code=code, category=category,
                question=" ".join(question).strip(),
                answer="\n".join(answer).strip()))

    for kind, payload in blocks:
        if kind != "paragraph":
            continue
        text = str(payload)
        if not text:
            continue
        heading = _match_heading(text)
        if heading is not None:
            flush()
            code, category, inline_question = heading
            question = [inline_question] if inline_question else []
            answer, in_answer = [], False
            continue
        if not code and not question:
            continue
        if _is_answer_heading(text):
            in_answer = True
            continue
        if _is_point_cell(text):
            continue
        if in_answer:
            answer.append(text)
        else:
            question.append(text)
    flush()
    return entries


__all__ = ["DocxFormatError", "parse_docx"]
