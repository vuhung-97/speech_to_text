"""FAQ administration API: CRUD, CSV import, reindex, stats."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel

from ..domain.faq.models import FaqEntry
from ..utils.errors import NotFoundError
from .deps import FaqServiceDep, TenantDep

router = APIRouter(tags=["faq"])

MAX_IMPORT_BYTES = 2 * 1024 * 1024


class EntryRequest(BaseModel):
    question: str = ""
    answer: str = ""
    category: str = ""


class EntryPatch(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    active: bool | None = None


def entry_json(entry: FaqEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "question": entry.question,
        "answer": entry.answer,
        "category": entry.category,
        "active": entry.active,
        "updated_at": entry.updated_at,
        "created_at": entry.created_at,
    }


@router.get("/faq/entries")
def list_entries(faq: FaqServiceDep, tenant: TenantDep, q: str | None = None,
                 category: str | None = None, active: bool | None = None,
                 limit: int = 50, offset: int = 0) -> dict[str, Any]:
    items = faq.list(tenant, query=q, category=category, active=active,
                     limit=limit, offset=offset)
    return {"ok": True, "items": [entry_json(item) for item in items]}


@router.post("/faq/entries")
def create_entry(request: EntryRequest, faq: FaqServiceDep,
                 tenant: TenantDep) -> dict[str, Any]:
    entry = faq.create(tenant, request.question, request.answer, request.category)
    return {"ok": True, "entry": entry_json(entry)}


@router.patch("/faq/entries/{entry_id}")
def update_entry(entry_id: str, request: EntryPatch, faq: FaqServiceDep,
                 tenant: TenantDep) -> dict[str, Any]:
    patch = {key: value for key, value in request.model_dump().items()
             if value is not None}
    try:
        entry = faq.update(entry_id, tenant, patch)
    except ValueError as exc:
        if "không tìm thấy" in str(exc):
            raise NotFoundError(str(exc)) from exc
        raise
    return {"ok": True, "entry": entry_json(entry)}


@router.delete("/faq/entries/{entry_id}")
def delete_entry(entry_id: str, faq: FaqServiceDep,
                 tenant: TenantDep) -> dict[str, Any]:
    if not faq.delete(entry_id, tenant):
        raise NotFoundError("không tìm thấy câu hỏi")
    return {"ok": True, "deleted": entry_id}


@router.post("/faq/import")
async def import_entries(tenant: TenantDep, faq: FaqServiceDep,
                         file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("tệp CSV quá lớn (tối đa 2 MB)")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("tệp CSV phải là UTF-8") from exc
    report = faq.import_csv(tenant, content)
    return {"ok": True, **report}


@router.post("/faq/reindex")
def reindex(faq: FaqServiceDep, tenant: TenantDep) -> dict[str, Any]:
    return {"ok": True, **faq.reindex(tenant)}


@router.get("/faq/stats")
def stats(request: Request, faq: FaqServiceDep, tenant: TenantDep) -> dict[str, Any]:
    return {"ok": True, **faq.stats(tenant),
            "embed_note": getattr(request.app.state, "embed_note", "")}
