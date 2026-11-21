"""Voice catalog: VieNeu presets plus voices cloned by the desktop app.

Reading the catalog never loads the model; it only reads JSON shipped with the
``vieneu`` package and the app's ``custom_voices.json``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def _voice_label(name: str, entry: dict[str, Any]) -> str:
    description = str(entry.get("description") or "").strip()
    label = f"{name} — {description}" if description else name
    return f"⭐ {label}" if entry.get("featured") else label


class VoiceCatalog:
    def __init__(self, custom_voices: Path) -> None:
        self._custom_voices = custom_voices

    def read_presets(self) -> tuple[dict[str, Any], str]:
        spec = importlib.util.find_spec("vieneu")
        if spec is None or not spec.origin:
            return {}, ""
        path = Path(spec.origin).parent / "assets" / "voices_v3_turbo.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}, ""
        presets = data.get("presets")
        return (presets if isinstance(presets, dict) else {}), str(data.get("default_voice") or "")

    def read_custom_voices(self) -> dict[str, dict[str, Any]]:
        """Cloned voices saved by the VieNeu desktop app (speaker embedding + codes)."""
        try:
            data = json.loads(self._custom_voices.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        voices = data.get("voices")
        if not isinstance(voices, dict):
            return {}
        return {
            name: entry
            for name, entry in voices.items()
            if isinstance(entry, dict) and entry.get("speaker_emb")
        }

    def voices(self) -> tuple[list[dict[str, Any]], str]:
        """Return ``(voices, default_id)`` without loading the model."""
        if importlib.util.find_spec("vieneu") is None:
            return [], ""
        presets, default = self.read_presets()
        entries: list[dict[str, Any]] = []

        ordered = sorted(
            presets.items(),
            key=lambda item: (item[1].get("featured") is None, item[1].get("featured") or 0),
        )
        for name, entry in ordered:
            entries.append({
                "id": name,
                "label": _voice_label(name, entry),
                "gender": str(entry.get("gender") or ""),
                "featured": bool(entry.get("featured")),
                "custom": False,
            })
        for name, entry in self.read_custom_voices().items():
            entries.append({
                "id": name,
                "label": _voice_label(name, entry),
                "gender": str(entry.get("gender") or ""),
                "featured": False,
                "custom": True,
            })
        if not default:
            default = entries[0]["id"] if entries else ""
        return entries, default


__all__ = ["VoiceCatalog"]
