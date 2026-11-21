"""Errors raised by the TTS layer."""


class TtsUnavailable(RuntimeError):
    """The optional TTS runtime or its model files are not installed."""


class TtsBusy(RuntimeError):
    """A long-form synthesis is already running (one at a time by design)."""


class TtsStorageError(RuntimeError):
    """Not enough free disk space for the requested audio."""


class TtsCancelled(RuntimeError):
    """The client cancelled a synthesis job."""


__all__ = ["TtsBusy", "TtsCancelled", "TtsStorageError", "TtsUnavailable"]
