"""Catalogue administration: validate, de-duplicate, import, reindex.

One responsibility: keep the catalogue internally consistent and the search
index fresh. Matching itself lives in the adapter; persistence in the repo.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

import numpy as np

from ..domain.faq.models import FaqEntry
from ..domain.faq.normalize import normalize_question
from ..domain.faq.rules import DUPLICATE_THRESHOLD, validate_entry
from ..ports.embedding import Embedder
from ..ports.faq import FaqRepository
from ..adapters.retrieval.sqlite_faq import SqliteFaqMatcher


class FaqService:
    def __init__(self, repository: FaqRepository, matcher: SqliteFaqMatcher,
                 embedder: Embedder | None = None) -> None:
        self._repo = repository
        self._matcher = matcher
        self._embedder = embedder or getattr(matcher, "_embedder", None)

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
        self._matcher.invalidate(tenant)
        return entry

    def update(self, entry_id: str, tenant: str, patch: dict) -> FaqEntry:
        existing = self._repo.get(entry_id, tenant)
        if existing is None:
            raise ValueError("không tìm thấy câu hỏi")
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
        self._matcher.invalidate(tenant)
        return updated

    def delete(self, entry_id: str, tenant: str) -> bool:
        deleted = self._repo.delete(entry_id, tenant)
        self._matcher.invalidate(tenant)
        return deleted

    # ---------------------------------------------------------------- indexing
    def reindex(self, tenant: str) -> dict[str, object]:
        self._matcher.invalidate(tenant)
        entries, matrix = self._matcher.ensure_index(tenant)
        return {
            "indexed": len(entries),
            "dim": int(matrix.shape[1]) if matrix.size else self._matcher.dim,
            "model": self._matcher.model_id,
            "version": self._matcher.version,
        }

    def stats(self, tenant: str) -> dict[str, object]:
        payload = dict(self._repo.stats(tenant))
        payload.update({
            "model": self._matcher.model_id,
            "version": self._matcher.version,
            "dim": self._matcher.dim,
            "threshold": self._matcher.threshold,
            "near_threshold": self._matcher.near_threshold,
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

        entries, matrix = self._matcher.ensure_index(tenant)
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

        self._matcher.invalidate(tenant)
        return report

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
