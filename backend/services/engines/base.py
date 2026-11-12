"""ASR engine contract + self-registering plugin registry.

Add a model by dropping one module into this folder::

    from ..engines.base import ASREngine
    from ...config.fields import Field

    class MyEngine(ASREngine):
        key = "my-model"            # id used in settings
        label = "My model (runtime)"

        @classmethod
        def fields(cls):
            return (Field("my_param", "engine", "My param", "int", 1),)

        @classmethod
        def is_available(cls):
            return True, ""

        def transcribe(self, audio):
            return "text", 0.1       # (text, real_time_factor)

Nothing else has to be edited: discovery imports every module in this package,
registers subclasses by ``key`` and the settings schema grows automatically.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from ...config.fields import EngineSpec, Field

_REGISTRY: dict[str, type["ASREngine"]] = {}
_LOCK = threading.Lock()
_DISCOVERED = False


class ASREngine(ABC):
    """One responsibility: turn 16 kHz mono audio into text."""

    key: str = ""
    label: str = ""

    def __init__(self, values: dict[str, Any]) -> None:
        self.values = dict(values)
        self.cpu_threads = int(self.values.get("cpu_threads", 2))
        self.compute_type = str(self.values.get("compute_type", "int8"))
        self.load_seconds = 0.0

    # -- contract ----------------------------------------------------------
    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> tuple[str, float]:
        """Return (text, real_time_factor = processing_time / audio_duration)."""

    def describe(self) -> dict[str, Any]:
        return {"model": self.key, "cpu_threads": self.cpu_threads,
                "compute_type": self.compute_type,
                "load_seconds": self.load_seconds}

    def close(self) -> None:
        """Optional cleanup when the engine is unloaded."""

    # -- plugin metadata ---------------------------------------------------
    @classmethod
    def fields(cls) -> tuple[Field, ...]:
        """Extra settings this engine needs (rendered automatically in the UI)."""
        return ()

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        """Return (ready, reason). ``reason`` is shown to the user when not ready."""
        return True, ""


# --------------------------------------------------------------------------
# Registry / discovery
# --------------------------------------------------------------------------
def register_engine(engine_cls: type[ASREngine]) -> None:
    """Explicit registration (used by tests and advanced plugins)."""
    if not getattr(engine_cls, "key", ""):
        raise ValueError("engine class needs a non-empty 'key'")
    with _LOCK:
        _REGISTRY[engine_cls.key] = engine_cls


def discover_engines(force: bool = False) -> dict[str, type[ASREngine]]:
    """Import every module in this package and register ASREngine subclasses."""
    global _DISCOVERED
    with _LOCK:
        if _DISCOVERED and not force:
            return dict(_REGISTRY)
        package_dir = Path(__file__).resolve().parent
        for info in pkgutil.iter_modules([str(package_dir)]):
            if info.name.startswith("_") or info.name == "base":
                continue
            module_name = f"{__package__}.{info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # a broken plugin must not kill the app
                print(f"[engine plugin skipped: {info.name}: {exc}]")
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (obj is not ASREngine and issubclass(obj, ASREngine)
                        and getattr(obj, "key", "") and not inspect.isabstract(obj)):
                    _REGISTRY[obj.key] = obj
        _DISCOVERED = True
        return dict(_REGISTRY)


def available_engines() -> dict[str, EngineSpec]:
    """Catalog used by settings/UI: key -> spec (label, own fields, availability)."""
    specs: dict[str, EngineSpec] = {}
    for key, engine_cls in sorted(discover_engines().items()):
        try:
            ready, reason = engine_cls.is_available()
        except Exception as exc:  # never let a probe break the catalog
            ready, reason = False, str(exc)
        specs[key] = EngineSpec(key=key, label=engine_cls.label or key,
                                fields=tuple(engine_cls.fields()), available=ready,
                                reason=reason)
    return specs


def create_engine(key: str, values: dict[str, Any]) -> ASREngine:
    registry = discover_engines()
    engine_cls = registry.get(key)
    if engine_cls is None:
        choices = ", ".join(registry) or "—"
        raise ValueError(f"model '{key}' không tồn tại (đang có: {choices})")
    ready, reason = engine_cls.is_available()
    if not ready:
        raise RuntimeError(f"model '{key}' chưa sẵn sàng: {reason}")
    return engine_cls(values)


__all__ = ["ASREngine", "available_engines", "create_engine", "discover_engines",
           "register_engine"]
