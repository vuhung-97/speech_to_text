"""Typed payloads shared by services and controllers (no HTTP, no audio)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CaptureStats:
    """Health of the microphone stream (proves no audio is being dropped)."""

    backend: str = "none"
    device: str = ""
    rate: int = 0
    frames: int = 0
    frames_per_sec: float = 0.0
    coverage: float = 0.0
    dropped: int = 0
    xruns: int = 0

    @classmethod
    def from_stats(cls, stats: dict[str, Any] | None) -> "CaptureStats":
        stats = stats or {}
        return cls(
            backend=str(stats.get("backend", "none")),
            device=str(stats.get("device", "")),
            rate=int(stats.get("rate", 0) or 0),
            frames=int(stats.get("frames", 0) or 0),
            frames_per_sec=float(stats.get("frames_per_sec", 0.0) or 0.0),
            coverage=float(stats.get("coverage", 0.0) or 0.0),
            dropped=int(stats.get("dropped", 0) or 0),
            xruns=int(stats.get("xruns", 0) or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"backend": self.backend, "device": self.device, "rate": self.rate,
                "frames": self.frames, "frames_per_sec": self.frames_per_sec,
                "coverage": self.coverage, "dropped": self.dropped,
                "xruns": self.xruns}


@dataclass(frozen=True)
class ReplaySegment:
    text: str
    audio_s: float
    decode_s: float

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "audio_s": self.audio_s, "decode_s": self.decode_s}


@dataclass(frozen=True)
class ReplayResult:
    """Outcome of decoding one file from samples/ with the current settings."""

    name: str
    text: str
    audio_s: float
    decode_s: float
    rtf: float
    truncated: bool = False
    segments: list[ReplaySegment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "text": self.text, "audio_s": self.audio_s,
                "decode_s": self.decode_s, "rtf": self.rtf,
                "truncated": self.truncated,
                "segments": [segment.to_dict() for segment in self.segments]}
