"""TempAudioStore: append while reading, seek, finalize, cleanup."""

from __future__ import annotations

import os
import sys
import time
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.audio.temp_store import (TempAudioStore, TempSession,
                                               cleanup_stale_sessions,
                                               directory_bytes)


@pytest.fixture()
def store(tmp_path: Path):
    item = TempAudioStore(tmp_path / "audio.wav", 48_000)
    yield item
    item.cleanup()


def test_append_then_read_and_seek(store: TempAudioStore) -> None:
    samples = np.full(1_000, 0.5, dtype=np.float32)
    assert store.append(samples) == 1_000
    assert store.append_pcm(b"\x00\x00" * 500) == 1_500

    assert store.total_samples == 1_500
    assert store.size_bytes == 3_000
    assert store.seconds == pytest.approx(1_500 / 48_000)

    assert len(store.read_pcm(0, 100)) == 200
    assert len(store.read_pcm(1_400, 1_000)) == 200   # clamped to what exists
    assert store.read_pcm(9_999, 10) == b""
    assert store.read_pcm(0, 0) == b""


def test_read_float_round_trip(store: TempAudioStore) -> None:
    store.append(np.array([0.0, 0.5, -0.5], dtype=np.float32))
    values = store.read_float(0, 3)
    assert values.tolist() == pytest.approx([0.0, 0.5, -0.5], abs=1e-4)


def test_finalize_patches_wav_header(store: TempAudioStore) -> None:
    store.append(np.zeros(4_800, dtype=np.float32))
    store.finalize()
    assert store.finalized

    with wave.open(str(store.path), "rb") as handle:
        assert handle.getnframes() == 4_800
        assert handle.getframerate() == 48_000
        assert handle.getsampwidth() == 2


def test_read_available_waits_then_returns(store: TempAudioStore) -> None:
    assert store.read_available(0, timeout=0.02) == b""

    store.append(np.zeros(480, dtype=np.float32))
    assert len(store.read_available(0, timeout=0.02)) == 960

    store.finalize()
    assert store.read_available(480, timeout=0.02) == b""


def test_fail_wakes_readers(store: TempAudioStore) -> None:
    store.fail(RuntimeError("boom"))
    assert store.finalized
    assert store.read_available(0, timeout=0.05) == b""
    with pytest.raises(RuntimeError):
        store.append(np.zeros(10, dtype=np.float32))


def test_cleanup_removes_file_and_directory(tmp_path: Path) -> None:
    session = TempSession(tmp_path, "job1")
    item = session.store("audio", 48_000)
    item.append(np.zeros(10, dtype=np.float32))
    assert item.path.is_file() and session.path.is_dir()

    session.cleanup()
    assert not session.path.exists()


def test_stale_sessions_are_swept(tmp_path: Path) -> None:
    fresh = TempSession(tmp_path, "fresh")
    stale = TempSession(tmp_path, "stale")
    old = time.time() - 48 * 3600
    os.utime(stale.path, (old, old))

    assert cleanup_stale_sessions(tmp_path, max_age_hours=24) == 1
    assert fresh.path.is_dir()
    assert not stale.path.exists()
    fresh.cleanup()


def test_directory_bytes(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 100)
    (tmp_path / "b.bin").write_bytes(b"y" * 50)
    assert directory_bytes(tmp_path) == 150
