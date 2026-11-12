"""Best-effort thread priorities so audio consumption wins over decoding.

Windows only; on other platforms every call is a silent no-op.
"""

from __future__ import annotations

import os

_THREAD_PRIORITY_HIGHEST = 2
_THREAD_PRIORITY_ABOVE_NORMAL = 1
_THREAD_PRIORITY_BELOW_NORMAL = -1
_THREAD_PRIORITY_LOWEST = -2


def _set(level: int) -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetThreadPriority(kernel32.GetCurrentThread(), level)
    except Exception:  # priority is a nicety, never a reason to fail
        pass


def raise_for_audio() -> None:
    """Call inside the thread that drains microphone blocks."""
    _set(_THREAD_PRIORITY_ABOVE_NORMAL)


def lower_for_decode() -> None:
    """Call inside the thread that runs the whisper model."""
    _set(_THREAD_PRIORITY_BELOW_NORMAL)


def lowest_for_background() -> None:
    """Call inside background jobs (model reload)."""
    _set(_THREAD_PRIORITY_LOWEST)
