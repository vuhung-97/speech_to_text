"""Conversation sessions: list, detail and delete (tenant scoped)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..utils.errors import NotFoundError
from .deps import AuditDep, SessionsRepoDep, TenantDep

router = APIRouter(tags=["sessions"])


@router.get("/sessions")
def list_sessions(sessions: SessionsRepoDep, tenant: TenantDep,
                  limit: int = 50, offset: int = 0) -> dict[str, Any]:
    items = sessions.list_sessions(tenant, limit=limit, offset=offset)
    return {"ok": True, "items": list(items), "limit": limit, "offset": offset}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, sessions: SessionsRepoDep,
                tenant: TenantDep) -> dict[str, Any]:
    session = sessions.get_session(session_id, tenant)
    if session is None:
        raise NotFoundError("không tìm thấy phiên hội thoại")
    return {"ok": True, **session}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, sessions: SessionsRepoDep,
                   audit: AuditDep, tenant: TenantDep) -> dict[str, Any]:
    if not sessions.delete_session(session_id, tenant):
        raise NotFoundError("không tìm thấy phiên hội thoại")
    audit.record(tenant=tenant, action="session.delete", target=session_id)
    return {"ok": True, "deleted": session_id}
