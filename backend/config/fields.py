"""Field/spec descriptors shared by settings and engine plugins (no dependencies)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    """One tunable setting. ``effect`` tells the pipeline what to do on change."""

    key: str
    group: str
    label: str
    kind: str  # enum | int | float | bool | text | device
    default: Any
    hint: str = ""
    effect: str = "live"  # live | engine | capture | vad
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    options: tuple[str, ...] = ()
    unit: str = ""
    advanced: bool = False
    mode_only: str | None = None  # only meaningful for this mode

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "group": self.group,
            "label": self.label,
            "kind": self.kind,
            "default": self.default,
            "hint": self.hint,
            "effect": self.effect,
            "min": self.minimum,
            "max": self.maximum,
            "step": self.step,
            "options": list(self.options),
            "unit": self.unit,
            "advanced": self.advanced,
            "mode_only": self.mode_only,
        }


@dataclass(frozen=True)
class EngineSpec:
    """What the settings/UI layer needs to know about one ASR engine plugin."""

    key: str
    label: str
    fields: tuple[Field, ...] = ()
    available: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "available": self.available,
                "reason": self.reason}
