"""Speech contract: text in, PCM16 blocks out, cancellable."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class SpeechSynthesizer(Protocol):
    """Streaming TTS with a bounded memory footprint regardless of text length."""

    sample_rate: int
    busy: bool

    def stream_pcm(self, text: str, voice: str | None = None) -> Iterator[bytes]:
        """Yield mono PCM16 little-endian blocks (~1 s) as they are produced."""
        ...

    def cancel(self) -> None:
        """Stop the active stream and release its temporary storage."""
        ...


__all__ = ["SpeechSynthesizer"]
