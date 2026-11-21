"""Bootstrap shared by the command-line tools in this folder.

Running a tool as a script puts ``tools/`` on ``sys.path``; this module then
adds the repository root so ``backend.*`` imports work, and normalises the
console encoding for Vietnamese output on Windows.
"""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> Path:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


__all__ = ["bootstrap"]
