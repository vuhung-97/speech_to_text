"""Speech contract: text in, PCM16 blocks out, cancellable.

The protocol covers both entry points the app uses:

- :meth:`SpeechSynthesizer.stream_pcm` — one-shot streaming (short text);
- the job API (``prepare_stream`` / ``stream_job`` / ``cancel``) — long-form
  synthesis written to a temporary WAV while it streams.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol


class SpeechAudioStore(Protocol):
    """Temporary audio written by one long-form job."""

    sample_rate: int
    size_bytes: int


class SpeechJobHandle(Protocol):
    """Handle returned by :meth:`SpeechSynthesizer.prepare_stream`."""

    id: str
    voice: str | None
    finalized: bool
    wav_path: Path
    seconds: float
    store: SpeechAudioStore


class SpeechSynthesizer(Protocol):
    """Streaming TTS with a bounded memory footprint regardless of text length."""

    sample_rate: int

    @property
    def busy(self) -> bool: ...

    def resolve_voice(self, voice: str | None = None) -> str | None: ...

    def stream_pcm(self, text: str, voice: str | None = None) -> Iterator[bytes]:
        """Yield mono PCM16 little-endian blocks (~1 s) as they are produced."""
        ...

    def prepare_stream(self, text: str, voice: str | None = None,
                       session_id: str | None = None) -> SpeechJobHandle: ...

    def stream_job(self, job: SpeechJobHandle) -> Iterator[bytes]: ...

    def cancel(self, job_id: str) -> bool:
        """Stop the active stream and release its temporary storage."""
        ...


__all__ = ["SpeechAudioStore", "SpeechJobHandle", "SpeechSynthesizer"]
