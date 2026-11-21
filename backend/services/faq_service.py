"""Catalogue administration: validate, de-duplicate, keep the index fresh.

One responsibility: keep the catalogue internally consistent and the search
index fresh. Matching itself lives in the adapter, persistence in the repo, and
the import formats in :mod:`.faq_import`; this class is the single facade the
controllers and :class:`FaqDocumentsService` depend on.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.faq.models import (FaqDocument, FaqEntry, FaqEntryNotFound,
                                 FaqOutline)
from ..domain.faq.normalize import normalize_question
from ..domain.faq.rules import validate_entry
from ..ports.embedding import Embedder
from ..ports.faq import FaqIndex, FaqRepository
from .faq_import import (CsvImportReport, FaqImportService,
                         OutlineImportReport)


class FaqService:
    def __init__(self, repository: FaqRepository, index: FaqIndex,
                 embedder: Embedder | None = None) -> None:
        self._repo = repository
        self._index = index
        self._imports = FaqImportService(repository, index, embedder)

    # ------------------------------------------------------------------- CRUD
    def list(self, tenant: str, **filters) -> Sequence[FaqEntry]:
        return self._repo.list(tenant, **filters)

    def create(self, tenant: str, question: str, answer: str,
               category: str = "") -> FaqEntry:
        clean_question, clean_answer, clean_category = validate_entry(
            question, answer, category)
        self._reject_exact_duplicate(tenant, clean_question)
        entry = self._repo.upsert(FaqEntry(
            id="",
            tenant_id=tenant,
            question=clean_question,
            answer=clean_answer,
            category=clean_category,
        ))
        self._index.invalidate(tenant)
        return entry

    def update(self, entry_id: str, tenant: str, patch: dict) -> FaqEntry:
        existing = self._repo.get(entry_id, tenant)
        if existing is None:
            raise FaqEntryNotFound("không tìm thấy câu hỏi")
        question = patch.get("question", existing.question)
        answer = patch.get("answer", existing.answer)
        category = patch.get("category", existing.category)
        active = bool(patch.get("active", existing.active))
        clean_question, clean_answer, clean_category = validate_entry(
            question, answer, category)
        if clean_question != existing.question:
            self._reject_exact_duplicate(tenant, clean_question, ignore_id=entry_id)
        updated = self._repo.upsert(FaqEntry(
            id=existing.id,
            tenant_id=tenant,
            question=clean_question,
            answer=clean_answer,
            category=clean_category,
            active=active,
        ))
        self._index.invalidate(tenant)
        return updated

    def delete(self, entry_id: str, tenant: str) -> bool:
        deleted = self._repo.delete(entry_id, tenant)
        self._index.invalidate(tenant)
        return deleted

    # ---------------------------------------------------------------- indexing
    def reindex(self, tenant: str) -> dict[str, object]:
        self._index.invalidate(tenant)
        entries, matrix = self._index.ensure_index(tenant)
        return {
            "indexed": len(entries),
            "dim": int(matrix.shape[1]) if matrix.size else self._index.dim,
            "model": self._index.model_id,
            "version": self._index.version,
        }

    def stats(self, tenant: str) -> dict[str, object]:
        payload = dict(self._repo.stats(tenant))
        payload.update({
            "model": self._index.model_id,
            "version": self._index.version,
            "dim": self._index.dim,
            "threshold": self._index.threshold,
            "near_threshold": self._index.near_threshold,
        })
        return payload

    # ------------------------------------------------------------------ import
    def import_csv(self, tenant: str, content: str) -> CsvImportReport:
        return self._imports.import_csv(tenant, content)

    def import_outline(self, tenant: str, entries: Sequence[FaqOutline],
                       *, document: FaqDocument) -> OutlineImportReport:
        return self._imports.import_outline(tenant, entries, document=document)

    # ----------------------------------------------------------------- helpers
    def _reject_exact_duplicate(self, tenant: str, question: str,
                                ignore_id: str | None = None) -> None:
        existing = self._repo.find_by_norm(tenant, normalize_question(question))
        if existing is not None and existing.id != ignore_id:
            raise ValueError("câu hỏi này đã có trong kho")


__all__ = ["FaqService"]
