"""FAQ administration API: CRUD, CSV import, reindex, stats."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..domain.faq.models import FaqEntry, FaqEntryNotFound
from ..services.tts_service import TtsBusy
from ..utils.errors import ApiError, NotFoundError
from .deps import AuditDep, FaqAudioDep, FaqServiceDep, TenantDep

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


class PrerenderRequest(BaseModel):
    voice: str | None = None


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
                 audit: AuditDep, tenant: TenantDep) -> dict[str, Any]:
    entry = faq.create(tenant, request.question, request.answer, request.category)
    audit.record(tenant=tenant, action="faq.create", target=entry.id,
                 detail=entry.question[:120])
    return {"ok": True, "entry": entry_json(entry)}


@router.patch("/faq/entries/{entry_id}")
def update_entry(entry_id: str, request: EntryPatch, faq: FaqServiceDep,
                 audit: AuditDep, tenant: TenantDep) -> dict[str, Any]:
    patch = {key: value for key, value in request.model_dump().items()
             if value is not None}
    try:
        entry = faq.update(entry_id, tenant, patch)
    except FaqEntryNotFound as exc:
        raise NotFoundError(str(exc)) from exc
    audit.record(tenant=tenant, action="faq.update", target=entry_id,
                 detail=",".join(sorted(patch)))
    return {"ok": True, "entry": entry_json(entry)}


@router.delete("/faq/entries/{entry_id}")
def delete_entry(entry_id: str, faq: FaqServiceDep, audit: AuditDep,
                 audio: FaqAudioDep, tenant: TenantDep) -> dict[str, Any]:
    if not faq.delete(entry_id, tenant):
        raise NotFoundError("không tìm thấy câu hỏi")
    audio.reset(entry_id, tenant)
    audit.record(tenant=tenant, action="faq.delete", target=entry_id)
    return {"ok": True, "deleted": entry_id}


@router.post("/faq/import")
async def import_entries(tenant: TenantDep, faq: FaqServiceDep,
                         audit: AuditDep,
                         file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("tệp CSV quá lớn (tối đa 2 MB)")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("tệp CSV phải là UTF-8") from exc
    report = faq.import_csv(tenant, content)
    audit.record(tenant=tenant, action="faq.import", target=file.filename or "",
                 detail=f"added={report.get('added')} errors={len(report.get('errors', []))}")
    return {"ok": True, **report}


@router.post("/faq/reindex")
def reindex(faq: FaqServiceDep, audit: AuditDep,
            tenant: TenantDep) -> dict[str, Any]:
    result = faq.reindex(tenant)
    audit.record(tenant=tenant, action="faq.reindex",
                 detail=f"indexed={result.get('indexed')}")
    return {"ok": True, **result}


@router.get("/faq/stats")
def stats(request: Request, faq: FaqServiceDep, tenant: TenantDep) -> dict[str, Any]:
    return {"ok": True, **faq.stats(tenant),
            "embed_note": getattr(request.app.state, "embed_note", "")}


@router.post("/faq/entries/{entry_id}/prerender")
def prerender(entry_id: str, request: PrerenderRequest, audio: FaqAudioDep,
              audit: AuditDep, tenant: TenantDep) -> dict[str, Any]:
    try:
        job = audio.start(entry_id, tenant, request.voice)
    except TtsBusy as exc:
        raise ApiError(str(exc), status_code=409) from exc
    except FaqEntryNotFound as exc:
        raise NotFoundError(str(exc)) from exc
    audit.record(tenant=tenant, action="faq.prerender", target=entry_id,
                 detail=job.voice)
    return {"ok": True, "job": audio.status(job.id)}


@router.get("/faq/prerender/{job_id}")
def prerender_status(job_id: str, audio: FaqAudioDep) -> dict[str, Any]:
    status = audio.status(job_id)
    if status is None:
        raise NotFoundError("không tìm thấy tác vụ tổng hợp")
    return {"ok": True, **status}


@router.get("/faq/entries/{entry_id}/audio")
def entry_audio(entry_id: str, audio: FaqAudioDep, tenant: TenantDep,
                voice: str = "") -> FileResponse:
    row = audio.cached(entry_id, tenant, voice)
    if row is None:
        raise NotFoundError("câu này chưa có bản đọc lưu sẵn")
    return FileResponse(
        str(row["path"]), media_type="audio/wav",
        filename=f"faq-{entry_id}.wav", headers={"Cache-Control": "no-store"})
