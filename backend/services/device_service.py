"""Input device catalog for the settings API."""

from __future__ import annotations

from typing import Any

import sounddevice as sd


def list_input_devices() -> list[dict[str, object]]:
    """One responsibility: describe input devices for the settings UI."""
    devices: list[dict[str, object]] = []
    try:
        for index, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) <= 0:
                continue
            devices.append({"index": index, "name": str(info["name"]),
                            "channels": int(info["max_input_channels"]),
                            "rate": int(info["default_samplerate"])})
    except Exception:
        return []
    return devices


