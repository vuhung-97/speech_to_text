"""Opaque primary keys shared by every SQLite repository."""

from __future__ import annotations

import uuid


def new_id() -> str:
    return uuid.uuid4().hex[:16]


__all__ = ["new_id"]
