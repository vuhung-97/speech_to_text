"""Tests for the settings store (no model, no microphone).

Checks:
    1. Defaults/schema, including engine-provided fields.
    2. Clamping, enum/number validation, unknown keys.
    3. Effect classification (live / engine / capture).
    4. Persistence round-trip and CLI overrides staying session-only.
    5. Warnings for risky values and unavailable engines.

Run:  python tests/test_settings.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.fields import EngineSpec, Field
from backend.config.settings import Settings


def catalog() -> dict[str, EngineSpec]:
    return {
        "fake-engine": EngineSpec("fake-engine", "Fake engine", (
            Field("fake_param", "engine", "Fake param", "float", 0.5,
                  minimum=0.0, maximum=1.0, step=0.1),
        )),
        "off-engine": EngineSpec("off-engine", "Off engine", (),
                                 available=False, reason="thiếu model"),
    }


def new_settings(tmp: Path) -> Settings:
    return Settings(tmp / "settings.json", catalog=catalog)


def test_defaults() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = new_settings(Path(tmp))
        values = settings.values()
        assert values["mode"] == "accurate"
        assert values["model"] == "fake-engine", "first catalog entry is the default"
        keys = {field["key"] for field in settings.schema()}
        assert {"model", "mode", "cpu_threads", "silence_hang",
                "threshold", "queue_size", "fake_param"} <= keys
        assert "fake_param" in keys, "engine-provided field appears in the schema"
    print("[1] Defaults OK - base + engine fields merged into the schema")


def test_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = new_settings(Path(tmp))

        result = settings.update({"cpu_threads": 99, "threshold": -1, "queue_size": 2.7})
        assert result["values"]["cpu_threads"] == 6
        assert result["values"]["threshold"] == 0.003
        assert result["values"]["queue_size"] == 3, "numeric rounding to int"

        result = settings.update({"mode": "nope", "unknown_key": 1, "fake_param": 5})
        assert "mode" in result["rejected"]
        assert "unknown_key" in result["rejected"]
        assert result["values"]["fake_param"] == 1.0, "engine field is clamped"

        result = settings.update({"model": "does-not-exist"})
        assert "model" in result["rejected"]
    print("[2] Validation OK - clamped and rejected as expected")


def test_effects() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = new_settings(Path(tmp))
        result = settings.update({"cpu_threads": 4, "silence_hang": 0.8})
        assert result["effects"]["engine"] == ["cpu_threads"]
        assert result["effects"]["capture"] == []
        assert set(result["applied"]) == {"cpu_threads", "silence_hang"}
    print("[3] Effects OK - engine / live split correctly")


def test_persistence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "settings.json"
        settings = Settings(path, catalog=catalog)
        settings.update({"cpu_threads": 4, "silence_hang": 1.2})
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert stored["version"] == 1
        assert stored["values"]["cpu_threads"] == 4

        reloaded = Settings(path, catalog=catalog)
        assert reloaded.get("cpu_threads") == 4
        assert reloaded.get("silence_hang") == 1.2

        reloaded.reset()
        assert reloaded.get("cpu_threads") == 2
        assert json.loads(path.read_text(encoding="utf-8"))["values"]["cpu_threads"] == 2
    print("[4] Persistence OK - save, reload and reset")


def test_cli_is_session_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "settings.json"
        settings = Settings(path, catalog=catalog)
        settings.apply_cli({"cpu_threads": 1})
        assert settings.get("cpu_threads") == 1

        settings.update({"silence_hang": 0.9})
        stored = json.loads(path.read_text(encoding="utf-8"))["values"]
        assert "cpu_threads" not in stored

        fresh = Settings(path, catalog=catalog)
        assert fresh.get("cpu_threads") == 2, "CLI override must not leak into the file"
        assert fresh.get("silence_hang") == 0.9
    print("[5] CLI OK - overrides stay in the session")


def test_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings = new_settings(Path(tmp))
        result = settings.update({"cpu_threads": 4})
        assert any("4 thread" in warning for warning in result["warnings"])

        result = settings.update({"model": "off-engine"})
        assert any("chưa sẵn sàng" in warning for warning in result["warnings"])

        settings.update({"cpu_threads": 2, "model": "fake-engine"})
        assert settings.warnings() == [], "no stale warnings after going back"
    print("[6] Warnings OK - risky values and unavailable engines are surfaced")


if __name__ == "__main__":
    test_defaults()
    test_validation()
    test_effects()
    test_persistence()
    test_cli_is_session_only()
    test_warnings()
    print("TEST_SETTINGS_DONE")
