"""Zipformer transducer (sherpa-onnx) - fast Vietnamese ASR, no hallucination."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any

import numpy as np

from ...config.constants import SAMPLE_RATE
from ...config.fields import Field
from ...config.paths import SHERPA_DIR
from .base import ASREngine

MODEL_DIR = SHERPA_DIR / "sherpa-onnx-zipformer-vi-30M-int8-2026-02-09"


class ZipformerEngine(ASREngine):
    key = "zipformer-vi-30M"
    label = "Zipformer Việt 30M (sherpa-onnx, int8)"

    @classmethod
    def fields(cls) -> tuple[Field, ...]:
        return (
            Field("max_active_paths", "engine", "Beam paths", "int", 4,
                  hint="Số nhánh beam của transducer. 1 = nhanh nhất, 4 = mặc định.",
                  minimum=1, maximum=8, step=1, advanced=True),
            Field("blank_penalty", "engine", "Blank penalty", "float", 0.0,
                  hint="Giảm từ bịa vào khoảng lặng. 0 = tắt; thử trong -2..2.",
                  minimum=-2.0, maximum=2.0, step=0.1, advanced=True),
        )

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec("sherpa_onnx") is None:
            return False, "thiếu package sherpa-onnx (pip install sherpa-onnx)"
        if not (MODEL_DIR / "encoder.int8.onnx").is_file():
            return False, f"thiếu model trong {MODEL_DIR}"
        return True, ""

    def __init__(self, values: dict[str, Any]) -> None:
        import sherpa_onnx

        super().__init__(values)
        base = Path(MODEL_DIR)
        started = time.perf_counter()
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(base / "encoder.int8.onnx"),
            decoder=str(base / "decoder.onnx"),
            joiner=str(base / "joiner.int8.onnx"),
            tokens=str(base / "tokens.txt"),
            num_threads=max(1, self.cpu_threads),
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
            modeling_unit="bpe",
            bpe_vocab=str(base / "bpe.model"),
            max_active_paths=int(self.values.get("max_active_paths", 4)),
            blank_penalty=float(self.values.get("blank_penalty", 0.0)),
        )
        self.load_seconds = round(time.perf_counter() - started, 2)
        print(f"Zipformer ready ({self.cpu_threads} threads) in {self.load_seconds:.1f}s")

    def transcribe(self, audio: np.ndarray) -> tuple[str, float]:
        started = time.perf_counter()
        stream = self.recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio)
        self.recognizer.decode_stream(stream)
        text = stream.result.text.strip().lower()
        duration = audio.size / SAMPLE_RATE
        return text, (time.perf_counter() - started) / max(duration, 1e-6)
