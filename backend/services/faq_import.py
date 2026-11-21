"""Catalogue import: CSV rows and outline documents.

One responsibility: turn an uploaded source into validated, de-duplicated
entries. Matching, CRUD and index freshness stay in :mod:`.faq_service`; this
module only owns the import formats and their report shape.
"""

from __future__ import annotations

import csv
import io
import threading
from collections.abc import Sequence

import numpy as np

from ..domain.faq.models import FaqDocument, FaqEntry, FaqOutline
from ..domain.faq.normalize import normalize_question
from ..domain.faq.rules import DUPLICATE_THRESHOLD, validate_entry
from ..ports.embedding import Embedder
from ..ports.faq import FaqIndex, FaqRepository


class FaqImportService:
    """Imports into one tenant's catalogue, serialised per process."""

    def __init__(self, repository: FaqRepository, index: FaqIndex,
                 embedder: Embedder | None = None) -> None:
        self._repo = repository
        self._index = index
        self._embedder = embedder
        # Two browser tabs uploading the same outline at once must not both
        # decide "code not seen yet" and insert a duplicate.
        self._lock = threading.Lock()

    # ------------------------------------------------------------------- CSV
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

    # --------------------------------------------------------------- outline
    def import_outline(self, tenant: str, entries: Sequence[FaqOutline],
                       *, document: FaqDocument) -> dict[str, object]:
        """Upsert parsed question/answer pairs into one question set.

        The pair ``(document, question code)`` is the identity, with an
        exact-question fallback inside the same set for entries without codes.
        Near-identical questions are *not* merged — the outline legitimately
        repeats wording, and merging would silently drop answers. Entries of the
        set whose codes left the file are switched off and reported as ``stale``.
        """
        with self._lock:
            return self._import_outline(tenant, entries, document)

    def _import_outline(self, tenant: str, entries: Sequence[FaqOutline],
                        document: FaqDocument) -> dict[str, object]:
        """Mutating core; callers hold ``_lock``."""
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

    # ---------------------------------------------------------------- helpers
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


__all__ = ["FaqImportService"]
