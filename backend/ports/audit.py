"""Audit trail contract for sensitive catalogue operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class AuditLog(Protocol):
    """Append-only record of deletes, imports and reindexes per tenant."""

    def record(self, *, tenant: str, action: str, target: str = "",
               detail: str = "") -> None: ...

    def list(self, tenant: str, limit: int = 50) -> Sequence[dict[str, object]]: ...


__all__ = ["AuditLog"]
