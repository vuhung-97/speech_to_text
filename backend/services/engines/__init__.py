"""ASR engine plugins: contract, registry and implementations.

Drop a new module in this folder (subclass ``ASREngine``) and it is discovered,
selectable in settings and rendered in the UI automatically.
"""

from .base import (ASREngine, available_engines, create_engine, discover_engines,
                   register_engine)

__all__ = ["ASREngine", "available_engines", "create_engine", "discover_engines",
           "register_engine"]
