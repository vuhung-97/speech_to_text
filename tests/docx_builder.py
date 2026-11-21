"""Minimal ``.docx`` writer used by the import tests (stdlib only).

Only ``word/document.xml`` is needed: the parser never reads styles or media.
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def paragraph(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def table(rows: list[list[str]]) -> str:
    body = "".join(
        "<w:tr>" + "".join(f"<w:tc>{paragraph(cell)}</w:tc>" for cell in row)
        + "</w:tr>"
        for row in rows)
    return f"<w:tbl>{body}</w:tbl>"


def docx(*blocks: str) -> bytes:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{"".join(blocks)}</w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def outline(answer: str = "Nội dung một.") -> bytes:
    """Two-question outline: a table block and an inline heading."""
    return docx(
        paragraph("Nhóm 1: Gồm 2 câu"),
        paragraph("Câu I.1.1"),
        table([
            ["Đồng chí hãy trình bày khái niệm “Tự động hóa chỉ huy”?", "4 đ"],
            ["Đáp án", ""],
            [answer, "0.5đ"],
            ["Nội dung hai.", "0.5đ"],
        ]),
        paragraph("Câu 2: Thủ đô Việt Nam là gì?"),
        table([
            ["Đáp án", ""],
            ["Hà Nội.", ""],
        ]),
    )


__all__ = ["docx", "outline", "paragraph", "table"]
