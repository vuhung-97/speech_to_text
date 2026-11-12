"""No-microphone smoke test for the pipeline (model + optional microphone).

Checks:
    1. UtteranceSegmenter emits a segment for a synthetic speech-like burst.
    2. ZipformerEngine loads and transcribes 1 s of silence without crashing.
    3. MicStream can open the default input device (if one exists) and report
       capture health (backend, coverage, dropped frames).

Run:  python smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.config.constants import BLOCK, BLOCK_DUR, SAMPLE_RATE
from backend.services.capture_service import MicStream
from backend.services.engines import create_engine
from backend.services.segmentation_service import UtteranceSegmenter


def test_segmenter() -> None:
    ep = UtteranceSegmenter()
    t = np.arange(BLOCK, dtype=np.float32) / SAMPLE_RATE
    burst = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    silence = np.zeros(BLOCK, np.float32)

    frames = [silence] * 5 + [burst] * 20 + [silence] * 12  # 2s of "speech"
    segs = [s for s in (ep.push(f) for f in frames) if s is not None]
    assert len(segs) == 1, f"expected 1 segment, got {len(segs)}"
    dur = segs[0].audio.size / SAMPLE_RATE
    assert 2.9 <= dur <= 3.1, f"unexpected segment duration {dur:.2f}s"
    print(f"[1] Segmenter OK - captured segment {dur:.2f}s")


def test_engine() -> None:
    engine = create_engine("zipformer-vi-30M", {"cpu_threads": 2})
    text, rtf = engine.transcribe(np.zeros(SAMPLE_RATE, np.float32))  # 1s silence
    assert isinstance(text, str)
    print(f"[2] Zipformer OK - 1s silence -> '{text}' (RTF {rtf:.2f})")


def test_mic() -> None:
    try:
        with MicStream() as mic:
            block = mic.read(timeout=2.0)
            assert block is not None and block.size == BLOCK
            stats = mic.stats()
            print(f"[3] MicStream OK - backend={stats['backend']} "
                  f"{stats['frames_per_sec']}/s coverage={stats['coverage'] * 100:.0f}% "
                  f"dropped={stats['dropped']} peak={np.abs(block).max():.4f}")
            for _ in range(30):  # 3 s of audio: how much actually arrived?
                mic.read(timeout=0.3)
            late = mic.stats()
            coverage = float(late["coverage"]) * 100
            note = "OK" if coverage >= 95 else "WARNING: audio is being dropped"
            print(f"[4] Capture {late['frames']} frames -> coverage {coverage:.0f}% "
                  f"dropped={late['dropped']} ({note})")
    except Exception as e:
        print(f"[3] MicStream WARNING - could not open input device: {e}")


if __name__ == "__main__":
    test_segmenter()
    test_engine()
    test_mic()
    print("SMOKE_TEST_DONE")
