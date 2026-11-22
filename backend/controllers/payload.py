"""The single success envelope for JSON endpoints.

Every handler returns ``{"ok": true, ...}``; building it here keeps the shape in
one place instead of repeating the literal in each controller.
"""

from __future__ import annotations

from typing import Any


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


__all__ = ["ok"]
