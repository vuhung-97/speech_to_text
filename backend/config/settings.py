"""Settings store: base fields + the active engine's own fields.

The engine catalog is injected (see :class:`backend.services.engines.EngineSpec`)
so this module stays independent of any concrete ASR implementation.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .fields import EngineSpec, Field
from .paths import SETTINGS_PATH

SETTINGS_VERSION = 1
CATALOG = Callable[[], dict[str, EngineSpec]]

MODEL_KEY = "model"

BASE_FIELDS: tuple[Field, ...] = (
    Field("mode", "mode", "Chế độ", "enum", "accurate",
          hint="accurate: chốt từng câu khi bạn ngừng nói. realtime: hiện chữ ngay khi nói.",
          options=("accurate", "realtime")),
    Field("cpu_threads", "engine", "CPU threads", "int", 2,
          hint="Số thread cho model. 2 là cân bằng; tăng nếu máy nhiều nhân rảnh.",
          effect="engine", minimum=1, maximum=6, step=1),
    Field("silence_hang", "vad", "Nghỉ để chốt câu", "float", 0.6,
          hint="Ngắn hơn: chốt nhanh nhưng dễ cắt giữa câu.",
          minimum=0.3, maximum=2.0, step=0.05, unit="s"),
    Field("threshold", "vad", "Ngưỡng mở micro", "float", 0.012,
          hint="RMS tuyệt đối. Phòng ồn thì tăng; nói nhỏ mà mất chữ thì giảm.",
          minimum=0.003, maximum=0.06, step=0.001),
    Field("noise_floor_ratio", "vad", "Hệ số nền ồn", "float", 4.0,
          hint="Ngưỡng = max(threshold, nền ồn × hệ số này).",
          minimum=2.0, maximum=8.0, step=0.5, advanced=True),
    Field("min_speech", "vad", "Độ dài tối thiểu", "float", 0.25,
          hint="Đoạn nói ngắn hơn mức này bị bỏ (lọc tiếng động).",
          minimum=0.1, maximum=1.0, step=0.05, unit="s"),
    Field("preroll", "vad", "Giữ trước khi nói", "float", 0.30,
          hint="Đệm audio trước khi phát hiện giọng để không mất âm tiết đầu.",
          minimum=0.0, maximum=0.5, step=0.05, unit="s"),
    Field("max_utterance", "vad", "Câu dài tối đa", "float", 15.0,
          hint="Vượt mức này sẽ chốt tạm một cửa sổ (gate giữ nguyên, không mất chữ).",
          minimum=8.0, maximum=28.0, step=1.0, unit="s", advanced=True),
    Field("decode_interval", "stream", "Nhịp cập nhật", "float", 0.9,
          hint="Chỉ dùng ở chế độ realtime: số giây audio giữa 2 lần decode.",
          minimum=0.2, maximum=1.5, step=0.1, unit="s", mode_only="realtime"),
    Field("queue_size", "stream", "Hàng đợi câu", "int", 4,
          hint="Số câu tối đa chờ nhận dạng; đầy thì câu cũ nhất bị bỏ.",
          minimum=1, maximum=8, step=1, advanced=True),
)


def model_field(specs: dict[str, EngineSpec]) -> Field:
    options = tuple(specs) or ("unavailable",)
    labels = "; ".join(f"{key} — {spec.label}" for key, spec in specs.items())
    return Field(MODEL_KEY, "engine", "Model", "enum", options[0],
                 options=options, effect="engine",
                 hint=("Model đang cắm: " + labels) if labels else "Chưa có engine nào.")


class Settings:
    """Holds current values, validates patches against the schema and persists."""

    def __init__(self, path: Path | str | None = None,
                 catalog: CATALOG | None = None) -> None:
        self._path = Path(path) if path else SETTINGS_PATH
        self._catalog = catalog or (lambda: {})
        self._lock = threading.RLock()
        self._values: dict[str, Any] = self._defaults()
        self._locked_by_cli: set[str] = set()
        self._warnings: list[str] = []
        self._load()

    # -- reads -------------------------------------------------------------
    def values(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._values)

    def get(self, key: str, fallback: Any = None) -> Any:
        with self._lock:
            return self._values.get(key, fallback)

    def warnings(self) -> list[str]:
        with self._lock:
            return list(self._warnings)

    @property
    def path(self) -> Path:
        return self._path

    def engine_specs(self) -> dict[str, EngineSpec]:
        return self._catalog()

    def fields(self) -> tuple[Field, ...]:
        """Base fields + the model selector + the active engine's own fields."""
        with self._lock:
            specs = self._catalog()
            active = self._values.get(MODEL_KEY)
            spec = specs.get(active) if isinstance(active, str) else None
            engine_fields = spec.fields if spec else ()
            return (model_field(specs), *BASE_FIELDS, *engine_fields)

    def schema(self) -> list[dict[str, Any]]:
        return [field.to_dict() for field in self.fields()]

    # -- writes ------------------------------------------------------------
    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        applied: list[str] = []
        rejected: dict[str, str] = {}

        with self._lock:
            known = self._known_fields()
            if MODEL_KEY in patch:
                field = known[MODEL_KEY]
                try:
                    model, _ = _coerce(field, patch[MODEL_KEY])
                except ValueError as exc:
                    rejected[MODEL_KEY] = str(exc)
                else:
                    if model != self._values.get(MODEL_KEY):
                        self._values[MODEL_KEY] = model
                        applied.append(MODEL_KEY)

            for key, raw in patch.items():
                if key == MODEL_KEY:
                    continue
                field = known.get(key)
                if field is None:
                    rejected[key] = "unknown key"
                    continue
                try:
                    value, _warning = _coerce(field, raw)
                except ValueError as exc:
                    rejected[key] = str(exc)
                    continue
                if value != self._values.get(key):
                    self._values[key] = value
                    applied.append(key)

            self._warnings = self._build_warnings()
            effects = {"engine": [k for k in applied if known[k].effect == "engine"],
                       "capture": [k for k in applied if known[k].effect == "capture"]}
            if applied:
                self._save_locked()
            return {
                "values": dict(self._values),
                "applied": applied,
                "effects": effects,
                "rejected": rejected,
                "warnings": list(self._warnings),
            }

    def apply_cli(self, patch: dict[str, Any]) -> None:
        """Session-only overrides: validated like any patch but never persisted."""
        with self._lock:
            known = self._known_fields()
            for key, raw in patch.items():
                if raw is None or key not in known:
                    continue
                try:
                    value, _ = _coerce(known[key], raw)
                except ValueError:
                    continue
                self._values[key] = value
                self._locked_by_cli.add(key)

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._values = self._defaults()
            self._warnings = self._build_warnings()
            self._save_locked()
            known = self._known_fields()
            return {
                "values": dict(self._values),
                "applied": [field.key for field in self.fields()],
                "effects": {
                    "engine": sorted(k for k, f in known.items() if f.effect == "engine"),
                    "capture": sorted(k for k, f in known.items() if f.effect == "capture"),
                },
                "rejected": {},
                "warnings": list(self._warnings),
            }

    # -- internals ---------------------------------------------------------
    def _defaults(self) -> dict[str, Any]:
        specs = self._catalog()
        values = {field.key: field.default for field in BASE_FIELDS}
        values[MODEL_KEY] = model_field(specs).default
        spec = specs.get(values[MODEL_KEY])
        if spec:
            values.update({field.key: field.default for field in spec.fields})
        return values

    def _known_fields(self) -> dict[str, Field]:
        specs = self._catalog()
        known = {field.key: field for field in BASE_FIELDS}
        known[MODEL_KEY] = model_field(specs)
        for spec in specs.values():  # fields of every engine stay valid (presets, switching)
            for field in spec.fields:
                known.setdefault(field.key, field)
        return known

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        stored = raw.get("values") if isinstance(raw, dict) else None
        if not isinstance(stored, dict):
            return
        known = self._known_fields()
        for key, value in stored.items():
            field = known.get(key)
            if field is None:
                continue
            try:
                self._values[key], _ = _coerce(field, value)
            except ValueError:
                continue
        self._warnings = self._build_warnings()

    def _save_locked(self) -> None:
        payload = {"version": SETTINGS_VERSION,
                   "values": {k: v for k, v in self._values.items()
                              if k not in self._locked_by_cli}}
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError:
            pass  # a read-only folder must not break dictation

    def _build_warnings(self) -> list[str]:
        warnings: list[str] = []
        if (self._values.get("cpu_threads") or 0) >= 4:
            warnings.append("Từ 4 thread, chi phí CPU tăng gấp đôi mà tốc độ chỉ nhanh hơn ~15%.")
        spec = self._catalog().get(str(self._values.get(MODEL_KEY)))
        if spec is not None and not spec.available:
            warnings.append(f"Model '{spec.key}' chưa sẵn sàng: {spec.reason}")
        return warnings


def _coerce(field: Field, raw: Any) -> tuple[Any, str | None]:
    """Return (value, warning). Raises ValueError when the input is unusable."""
    if field.kind == "bool":
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, (int, float)) and raw in (0, 1):
            return bool(raw), None
        raise ValueError("expected true/false")

    if field.kind in ("int", "float"):
        if isinstance(raw, bool) or raw is None:
            raise ValueError("expected a number")
        try:
            number = float(raw)
        except (TypeError, ValueError):
            raise ValueError("expected a number") from None
        if number != number:  # NaN
            raise ValueError("expected a number")
        if field.minimum is not None:
            number = max(field.minimum, number)
        if field.maximum is not None:
            number = min(field.maximum, number)
        if field.kind == "int":
            return int(round(number)), None
        return round(number, 4), None

    if field.kind == "enum":
        text = str(raw).strip()
        if text not in field.options:
            raise ValueError(f"must be one of {', '.join(field.options)}")
        return text, None

    if field.kind == "device":
        return str(raw).strip(), None  # kept for older settings files

    raise ValueError(f"unsupported field kind: {field.kind}")


__all__ = ["BASE_FIELDS", "MODEL_KEY", "Settings", "model_field"]
