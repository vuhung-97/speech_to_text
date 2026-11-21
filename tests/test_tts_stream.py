"""Long-form streaming: order, limits, cancellation and flat memory."""

from __future__ import annotations

import sys
import tracemalloc
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.text.limits import MAX_TTS_WORDS, TextTooLong
from backend.services.tts_service import (SpeechJob, TtsBusy, TtsService,
                                          TtsStorageError)

SAMPLE_RATE = 48_000


class FakeEngine:
    """One second of audio per block, no model, no ONNX."""

    sample_rate = SAMPLE_RATE

    def __init__(self, seconds: int = 3, amplitude: float = 0.25) -> None:
        self.seconds = seconds
        self.amplitude = amplitude
        self.calls: list[str] = []

    def infer_stream(self, text: str, voice=None, **kwargs):
        self.calls.append(text)
        for _ in range(self.seconds):
            yield np.full(48_000, self.amplitude, dtype=np.float32)

    def infer(self, text: str, voice=None, **kwargs):
        return np.zeros(48_000, dtype=np.float32)


class FakeTts(TtsService):
    def __init__(self, tmp_path: Path, seconds: int = 3, **kwargs) -> None:
        super().__init__(temp_root=tmp_path, **kwargs)
        self.engine = FakeEngine(seconds)

    def available(self):  # noqa: D102 - test double
        return True, ""

    def voices(self):  # noqa: D102 - test double
        return ([{"id": "Mai Anh"}, {"id": "Khác"}], "Mai Anh")

    def _ensure_engine(self):  # noqa: D102 - test double
        return self.engine


@pytest.fixture()
def service(tmp_path: Path):
    item = FakeTts(tmp_path)
    yield item
    item.shutdown()


def test_stream_writes_wav_and_returns_blocks(service: FakeTts, tmp_path: Path) -> None:
    statuses: list[dict] = []
    total = 0
    for block in service.synthesize_stream("Một đoạn văn bản ngắn.\n\nĐoạn thứ hai."):
        assert len(block) % 2 == 0
        total += len(block) // 2
        if service._store.active is not None:
            statuses.append(service.job_status(service._store.active.id))

    # two paragraphs → 3 s each plus a 0.35 s breath between them
    expected = 2 * 3 * SAMPLE_RATE + int(0.35 * SAMPLE_RATE)
    assert total == expected
    assert statuses and statuses[-1]["progress"] > 0

    job = next(iter(service._store.values()))
    assert job.finalized
    assert service.job_path(job.id) is not None
    assert job.wav_path.is_file()


def test_voice_is_resolved_and_rejected(service: FakeTts) -> None:
    service.prepare_stream("xin chào", voice="Khác")
    service.shutdown()
    with pytest.raises(ValueError, match="không có trong danh sách"):
        service.prepare_stream("xin chào", voice="Không tồn tại")


def test_empty_and_too_long_text_are_rejected(service: FakeTts) -> None:
    with pytest.raises(ValueError, match="chưa có văn bản"):
        service.prepare_stream("   ")
    with pytest.raises(TextTooLong):
        service.prepare_stream(" ".join(["từ"] * (MAX_TTS_WORDS + 1)))


def test_only_one_job_at_a_time(service: FakeTts) -> None:
    service.prepare_stream("xin chào")
    with pytest.raises(TtsBusy):
        service.prepare_stream("câu hỏi khác")


def test_quota_rejects_impossible_job(tmp_path: Path) -> None:
    small = FakeTts(tmp_path, quota_mb=1)
    try:
        with pytest.raises(TtsStorageError):
            small.prepare_stream("từ " * 1_000)  # ~28 MB estimate > 1 MB quota
    finally:
        small.shutdown()


def test_cancel_removes_temp_directory(service: FakeTts) -> None:
    job = service.prepare_stream("Một câu rất dài để huỷ giữa chừng.")
    stream = service.stream_job(job)
    next(stream)  # start
    directory = job.session.path
    assert directory.is_dir()

    assert service.cancel(job.id) is True
    with pytest.raises(StopIteration):
        while True:
            next(stream)

    assert not directory.exists()
    assert service.job_status(job.id) is None


def test_shutdown_cleans_everything(service: FakeTts) -> None:
    job = service.prepare_stream("Một câu ngắn.")
    path = job.session.path
    service.shutdown()
    assert not path.exists()
    assert service.busy is False


def test_stream_memory_is_flat(service: FakeTts, tmp_path: Path) -> None:
    service.engine = FakeEngine(seconds=200)

    tracemalloc.start()
    total = 0
    for block in service.synthesize_stream("câu " * 500):
        total += len(block)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert total == 200 * SAMPLE_RATE * 2
    assert peak < 12 * 2**20, f"peak {peak / 2**20:.1f} MB for 200 s of audio"
