"""Catalogue administration: validate, de-duplicate, import, reindex.

One responsibility: keep the catalogue internally consistent and the search
index fresh. Matching itself lives in the adapter; persistence in the repo.
"""

from __future__ import annotations

import csv
import io
import threading
from collections.abc import Sequence

import numpy as np

from ..domain.faq.models import (FaqDocument, FaqEntry, FaqEntryNotFound,
                                 FaqOutline)
from ..domain.faq.normalize import normalize_question
from ..domain.faq.rules import DUPLICATE_THRESHOLD, validate_entry
from ..ports.embedding import Embedder
from ..ports.faq import FaqIndex, FaqRepository


class FaqService:
    def __init__(self, repository: FaqRepository, index: FaqIndex,
                 embedder: Embedder | None = None) -> None:
        self._repo = repository
        self._index = index
        self._embedder = embedder
        # Two browser tabs uploading the same outline at once must not both
        # decide "code not seen yet" and insert a duplicate.
        self._import_lock = threading.Lock()

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
    def import_csv(self, tenant: str, content: str) -> dict[str, object]:
        rows = list(csv.DictReader(io.StringIO((content or "").lstrip("\ufeff"))))
        report: dict[str, object] = {
            "total": len(rows),
            "added": 0,
            "duplicates": [],
            "errors": [],
        }
        if not rows:
            return report

        entries, matrix = self._index.ensure_index(tenant)
        known = {normalize_question(entry.question) for entry in entries}
        accepted: list[np.ndarray] = []

        for index, row in enumerate(rows, start=2):  # header is line 1
            question = (row.get("question") or row.get("câu hỏi") or "").strip()
            answer = (row.get("answer") or row.get("câu trả lời") or "").strip()
            category = (row.get("category") or row.get("danh mục") or "").strip()
            try:
                clean_question, clean_answer, clean_category = validate_entry(
                    question, answer, category)
            except ValueError as exc:
                report["errors"].append({"row": index, "error": str(exc)})
                continue

            normalized = normalize_question(clean_question)
            if normalized in known:
                report["duplicates"].append({
                    "row": index, "question": clean_question, "score": 1.0})
                continue

            score = self._duplicate_score(clean_question, matrix, accepted)
            if score >= DUPLICATE_THRESHOLD:
                report["duplicates"].append({
                    "row": index, "question": clean_question,
                    "score": round(float(score), 4)})
                continue

            self._repo.upsert(FaqEntry(
                id="", tenant_id=tenant, question=clean_question,
                answer=clean_answer, category=clean_category))
            known.add(normalized)
            vector = self._vector(clean_question)
            if vector is not None:
                accepted.append(vector)
            report["added"] = int(report["added"]) + 1

        self._index.invalidate(tenant)
        return report

    def import_outline(self, tenant: str, entries: Sequence[FaqOutline],
                       *, document: FaqDocument) -> dict[str, object]:
        """Upsert parsed question/answer pairs into one question set.

        The pair ``(document, question code)`` is the identity, with an
        exact-question fallback inside the same set for entries without codes.
        Near-identical questions are *not* merged — the outline legitimately
        repeats wording, and merging would silently drop answers. Entries of the
        set whose codes left the file are switched off and reported as ``stale``.
        """
        with self._import_lock:
            return self._import_outline(tenant, entries, document)

    def _import_outline(self, tenant: str, entries: Sequence[FaqOutline],
                        document: FaqDocument) -> dict[str, object]:
        """Mutating core; callers hold ``_import_lock``."""
        report: dict[str, object] = {
            "total": len(entries),
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "stale": 0,
            "errors": [],
            "changed": [],
        }
        kept_codes: set[str] = set()

        for position, item in enumerate(entries, start=1):
            if item.code:
                kept_codes.add(item.code)
            try:
                clean_question, clean_answer, clean_category = validate_entry(
                    item.question, item.answer, item.category)
            except ValueError as exc:
                report["errors"].append(
                    {"row": position, "code": item.code, "error": str(exc)})
                continue

            target = self._import_target(tenant, document, item.code, clean_question)
            if (target is not None and target.question == clean_question
                    and target.answer == clean_answer):
                report["skipped"] = int(report["skipped"]) + 1
                continue

            saved = self._repo.upsert(FaqEntry(
                id=target.id if target else "",
                tenant_id=tenant,
                question=clean_question,
                answer=clean_answer,
                category=clean_category or (target.category if target else ""),
                active=True,
                source_file=document.name,
                source_ref=item.code,
                document_id=document.id,
            ))
            if target is None:
                report["added"] = int(report["added"]) + 1
            else:
                report["updated"] = int(report["updated"]) + 1
                report["changed"].append(saved.id)

        report["stale"] = self._repo.deactivate_missing(
            tenant, document.id, kept_codes)
        self._index.invalidate(tenant)
        return report

    def _import_target(self, tenant: str, document: FaqDocument, code: str,
                       question: str) -> FaqEntry | None:
        if code:
            by_source = self._repo.find_by_source(tenant, document.id, code)
            if by_source is not None:
                return by_source
        return self._repo.find_by_norm_in_document(
            tenant, document.id, normalize_question(question))

    # ----------------------------------------------------------------- helpers
    def _reject_exact_duplicate(self, tenant: str, question: str,
                                ignore_id: str | None = None) -> None:
        existing = self._repo.find_by_norm(tenant, normalize_question(question))
        if existing is not None and existing.id != ignore_id:
            raise ValueError("câu hỏi này đã có trong kho")

    def _vector(self, question: str) -> np.ndarray | None:
        if self._embedder is None:
            return None
        return np.asarray(self._embedder.embed_documents([question])[0],
                          dtype=np.float32)

    def _duplicate_score(self, question: str, matrix: np.ndarray,
                         accepted: list[np.ndarray]) -> float:
        score = 0.0
        vector = self._vector(question)
        if vector is None:
            return score
        if matrix.size:
            score = max(score, float(np.max(matrix @ vector)))
        for other in accepted:
            if other.shape == vector.shape:
                score = max(score, float(np.dot(other, vector)))
        return score


__all__ = ["FaqService"]
