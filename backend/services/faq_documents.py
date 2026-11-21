"""Question-set administration: one uploaded outline = one document.

This service resolves *which* document an upload belongs to (same content,
newer version, or a brand-new set), delegates entry upserts to the catalogue
service, keeps ``entry_count`` fresh, and owns rename/delete flows. Matching and
index freshness belong elsewhere; this service only mutates the sets.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from ..domain.faq.models import (FaqDocument, FaqDocumentNotFound, FaqOutline,
                                 MAX_DOCUMENT_NAME_CHARS, outline_fingerprint)
from ..ports.faq import FaqDocumentRepository, FaqIndex, FaqRepository
from .faq_service import FaqService

_UNSAFE_NAME = re.compile(r"[\\/:*?\"<>|\x00-\x1f]+")


class FaqDocumentsService:
    def __init__(self, documents: FaqDocumentRepository, entries: FaqRepository,
                 catalogue: FaqService, index: FaqIndex) -> None:
        self._documents = documents
        self._entries = entries
        self._catalogue = catalogue
        self._index = index

    # ------------------------------------------------------------------- list
    def list(self, tenant: str) -> Sequence[FaqDocument]:
        return self._documents.list(tenant)

    def get(self, document_id: str, tenant: str) -> FaqDocument:
        document = self._documents.get(document_id, tenant)
        if document is None:
            raise FaqDocumentNotFound("không tìm thấy bộ đề")
        return document

    # ----------------------------------------------------------------- import
    def import_document(self, tenant: str, source_name: str,
                        pairs: Sequence[FaqOutline]) -> dict[str, object]:
        """Resolve the document for an upload, then upsert its entries.

        Returns the catalogue report plus ``document`` and ``reason``:
        ``unchanged`` (same content, skipped), ``updated`` (newer version of an
        existing set), or ``created`` (a brand-new set).
        """
        name = _document_name(source_name)
        fingerprint = outline_fingerprint(pairs)

        same_content = self._documents.find_by_hash(tenant, fingerprint)
        if same_content is not None:
            report = {"total": len(pairs), "added": 0, "updated": 0,
                      "skipped": len(pairs), "stale": 0, "errors": [],
                      "changed": []}
            self._touch_count(tenant, same_content)
            return {"ok": True, **report, "document": _document_json(same_content),
                    "reason": "unchanged"}

        document = self._documents.find_by_name(tenant, name)
        if document is None:
            document = self._documents.create(tenant, name, fingerprint)
            reason = "created"
        else:
            reason = "updated"
            document = self._documents.update(
                document.id, tenant, content_hash=fingerprint)

        report = self._catalogue.import_outline(tenant, pairs, document=document)
        refreshed = self._touch_count(tenant, document)
        return {"ok": True, **report, "document": _document_json(refreshed),
                "reason": reason}

    # ---------------------------------------------------------------- rename
    def rename(self, document_id: str, tenant: str, name: str) -> FaqDocument:
        self.get(document_id, tenant)
        clean = _document_name(name)
        existing = self._documents.find_by_name(tenant, clean)
        if existing is not None and existing.id != document_id:
            raise ValueError("đã có bộ đề trùng tên này")
        updated = self._documents.update(document_id, tenant, name=clean)
        return updated or self.get(document_id, tenant)

    # ---------------------------------------------------------------- delete
    def delete(self, document_id: str, tenant: str) -> dict[str, object]:
        document = self.get(document_id, tenant)
        entry_ids = self._entries.delete_by_document(tenant, document_id)
        self._documents.delete(document_id, tenant)
        self._index.invalidate(tenant)
        return {"id": document_id, "name": document.name,
                "deleted_entries": len(entry_ids), "entry_ids": entry_ids}

    # ---------------------------------------------------------------- helpers
    def _touch_count(self, tenant: str, document: FaqDocument) -> FaqDocument:
        count = self._entries.count_in_document(tenant, document.id)
        updated = self._documents.update(document.id, tenant, entry_count=count)
        return updated or document


def _document_name(source_name: str) -> str:
    """Readable, length-capped label; the file name unless it is unusable."""
    name = _UNSAFE_NAME.sub(" ", Path(source_name or "").name).strip()
    if not name or name in {".", ".."}:
        name = "bộ đề mới"
    return name[:MAX_DOCUMENT_NAME_CHARS]


def _document_json(document: FaqDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "name": document.name,
        "entry_count": document.entry_count,
        "content_hash": document.content_hash[:12],
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


__all__ = ["FaqDocumentsService"]
