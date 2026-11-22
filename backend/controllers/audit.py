"""Audit trail for sensitive operations (tenant scoped)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .deps import AuditDep, TenantDep
from .payload import ok

router = APIRouter(tags=["audit"])


@router.get("/audit")
def list_audit(audit: AuditDep, tenant: TenantDep,
               limit: int = 50) -> dict[str, Any]:
    return ok(items=list(audit.list(tenant, limit=limit)))
