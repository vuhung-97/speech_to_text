"""Voice activity + utterance segmentation (pure logic, no audio devices).

EnergyGate decides whether one 100 ms frame is speech. UtteranceSegmenter groups
frames into utterances (with preroll, silence hang and window flush) and
LocalAgreement commits a stable word prefix for the realtime draft.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..config.constants import BLOCK_DUR


class EnergyGate:
    """One responsibility: decide whether one frame is speech.

    Two rules keep the gate from locking onto a voice (which swallowed whole
    minutes of audio):

    1. The ambient floor only learns from frames that already look like
       ambience (below the current threshold) - loud frames never raise it.
    2. The threshold can never exceed ~30% of the recent peak, so a quiet
       microphone (low gain) still detects its own speech instead of treating
       it as noise floor.
    """

    PEAK_RATIO = 0.30
    EXIT_RATIO = 0.5
    PEAK_WINDOW_S = 10.0

    def __init__(self, start_th: float = 0.012, floor_ratio: float = 4.0,
                 smoothing: float = 0.05) -> None:
        self.start_th = start_th
        self.floor_ratio = floor_ratio
        self.smoothing = smoothing
        self.noise_floor = 1.0e-3
        self._recent: deque[float] = deque(maxlen=int(self.PEAK_WINDOW_S / BLOCK_DUR))

    def _threshold(self) -> float:
        peak = max(self._recent) if self._recent else 0.0
        absolute = max(self.start_th, self.noise_floor * self.floor_ratio)
        relative = max(self.start_th * 0.5, peak * self.PEAK_RATIO)
        return min(absolute, relative)

    def _limit(self, in_speech: bool) -> float:
        """Hysteresis: keep speaking on a lower bar than it takes to start."""
        return self._threshold() * (self.EXIT_RATIO if in_speech else 1.0)

    def resume(self) -> None:
        """Forget pre-pause loudness so the threshold rebuilds from current audio.

        The 10 s peak window would otherwise keep the threshold high for the
        first seconds after resuming, which makes a quiet microphone deaf.
        """
        self._recent.clear()

    def observe(self, rms: float) -> None:
        """Track peak/floor without deciding - keeps the gate warm while paused."""
        self._recent.append(rms)
        if rms < self._threshold():
            self.noise_floor = (1.0 - self.smoothing) * self.noise_floor + self.smoothing * rms

    def is_speech(self, rms: float, in_speech: bool = False) -> bool:
        self._recent.append(rms)
        limit = self._limit(in_speech)
        # the floor only learns from frames that look like ambience, and never
        # while speech is ongoing (mid-speech dips would poison it)
        if rms < limit and not in_speech:
            self.noise_floor = (1.0 - self.smoothing) * self.noise_floor + self.smoothing * rms
        return rms >= limit


@dataclass(frozen=True)
class SegmenterConfig:
    """Timing knobs for one utterance."""

    preroll: float = 0.30        # s kept before speech onset (protects first syllable)
    silence_hang: float = 0.70   # s of trailing silence that closes the utterance
    min_speech: float = 0.25     # discard blips shorter than this
    max_utterance: float = 24.0  # flush before the model window overflows
    min_partial: float = 0.35    # shortest audio worth decoding mid-utterance


@dataclass(frozen=True)
class FinalAudio:
    """Audio handed to a full (non-partial) decode."""

    audio: np.ndarray
    hard_end: bool  # True: real silence closed the sentence, False: window flush


class UtteranceSegmenter:
    """One responsibility: accumulate 100 ms frames into a single live utterance.

    ``push`` returns audio only when the utterance is complete (trailing silence
    or max length); ``snapshot`` exposes the in-progress audio for partial decode.
    """

    def __init__(self, config: SegmenterConfig | None = None,
                 gate: EnergyGate | None = None) -> None:
        self.config = config or SegmenterConfig()
        self.gate = gate or EnergyGate()
        self.speaking = False
        self._preroll: list[np.ndarray] = []
        self._preroll_limit = max(1, int(round(self.config.preroll / BLOCK_DUR)))
        self._frames: list[np.ndarray] = []
        self._speech = 0.0
        self._silence = 0.0

    def push(self, frame: np.ndarray) -> FinalAudio | None:
        rms = _rms(frame)
        voiced = self.gate.is_speech(rms, self.speaking)

        if not self.speaking:
            if not voiced:
                self._preroll.append(frame)
                del self._preroll[:-self._preroll_limit]
                return None
            self.speaking = True
            self._frames = self._preroll + [frame]
            self._preroll = []
            self._speech = BLOCK_DUR
            self._silence = 0.0
            return None

        self._frames.append(frame)
        if voiced:
            self._silence = 0.0
            self._speech += BLOCK_DUR
        else:
            self._silence += BLOCK_DUR

        if self._silence >= self.config.silence_hang:
            return self._close(hard_end=True)
        if self._speech >= self.config.max_utterance:
            return self._close(hard_end=False)
        return None

    def snapshot(self) -> np.ndarray | None:
        """Current utterance audio, or None while too short to be useful."""
        if not self._frames:
            return None
        if len(self._frames) * BLOCK_DUR < self.config.min_partial:
            return None
        return np.concatenate(self._frames)

    def flush(self) -> FinalAudio | None:
        """Force-close the current utterance (file replay, shutdown)."""
        if not self._frames:
            self.reset()
            return None
        return self._close(hard_end=True)

    def reset(self) -> None:
        self.speaking = False
        self._preroll = []
        self._frames = []
        self._speech = 0.0
        self._silence = 0.0

    def _close(self, hard_end: bool) -> FinalAudio | None:
        frames, speech = self._frames, self._speech
        self._frames = []
        self._speech = 0.0
        self._silence = 0.0
        # A window flush (hard_end=False) happens mid-speech: keep the gate
        # locked in speech mode, otherwise it re-learns the noise floor from
        # the speaker's voice and drops everything until the next real pause.
        self.speaking = not hard_end
        if not frames or speech < self.config.min_speech:
            return None
        return FinalAudio(np.concatenate(frames), hard_end)


class LocalAgreement:
    """One responsibility: grow a stable word prefix across consecutive hypotheses.

    Two hypotheses over the same growing audio agree on the words they are sure
    about; the common prefix is safe to show as final, the rest is tentative.
    """

    def __init__(self) -> None:
        self._stable: list[str] = []
        self._previous: list[str] = []

    @property
    def stable_text(self) -> str:
        return " ".join(self._stable)

    def update(self, hypothesis: str) -> tuple[str, str]:
        """Return (stable_text, tentative_text) for ``hypothesis``."""
        words = hypothesis.split()
        agreed = 0
        limit = min(len(self._previous), len(words))
        while agreed < limit and self._previous[agreed] == words[agreed]:
            agreed += 1
        if agreed > len(self._stable):
            self._stable = words[:agreed]
        self._previous = words

        if words[:len(self._stable)] == self._stable:
            tentative = words[len(self._stable):]
        else:  # the model revised a committed word: keep the prefix, drop the clash
            shared = 0
            while (shared < min(len(self._stable), len(words))
                   and self._stable[shared] == words[shared]):
                shared += 1
            tentative = words[shared:]
        return self.stable_text, " ".join(tentative)

    def reset(self) -> None:
        self._stable.clear()
        self._previous.clear()


def build_segmenter(values: dict[str, Any]) -> UtteranceSegmenter:
    """Build a segmenter from flat settings values (shared by live + replay)."""
    config = SegmenterConfig(
        preroll=float(values["preroll"]),
        silence_hang=float(values["silence_hang"]),
        min_speech=float(values["min_speech"]),
        max_utterance=float(values["max_utterance"]),
    )
    gate = EnergyGate(start_th=float(values["threshold"]),
                      floor_ratio=float(values["noise_floor_ratio"]))
    return UtteranceSegmenter(config, gate=gate)


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0


__all__ = ["FinalAudio", "LocalAgreement", "SegmenterConfig",
           "UtteranceSegmenter", "build_segmenter"]
