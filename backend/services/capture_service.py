"""Audio capture: microphones -> 16 kHz mono 100 ms frames.

InputProber finds a working device configuration, Resampler converts native
formats to 16 kHz mono, MicStream prefers a callback stream and falls back to
short bursts on devices where callbacks never fire.
"""

from __future__ import annotations

import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd

from ..config.constants import BLOCK, BLOCK_DUR, SAMPLE_RATE
from ..utils import priority


class InputProber:
    """One responsibility: find an input (device, rate, channels, dtype) that opens."""

    # Known-good fallbacks for this laptop (Intel SST mic): WDM-KS arrays work
    # even while MME/WASAPI are blocked by the microphone privacy switch.
    FALLBACKS = [(14, 16_000, 4, "int16"), (13, 48_000, 2, "float32")]

    def __init__(self, explicit: int | str | None) -> None:
        self.explicit = explicit

    def candidates(self):
        if self.explicit is not None:
            yield self.explicit, 16_000, 1, "float32"
            yield self.explicit, 48_000, 2, "float32"
            return
        yield None, 16_000, 1, "float32"   # OS default mic (best case)
        yield None, 48_000, 2, "float32"
        for c in self.FALLBACKS:
            yield c

    def find(self) -> tuple[int | str, int, int, str]:
        last_err = None
        for dev, rate, ch, dtype in self.candidates():
            try:
                with sd.InputStream(samplerate=rate, channels=ch, dtype=dtype,
                                    device=dev, blocksize=0,
                                    callback=lambda *_: None):  # WDM-KS forbids blocking API
                    name = sd.query_devices(dev if dev is not None else
                                            sd.default.device[0])["name"]
                    print(f"Input device: '{name}' @ {rate} Hz, {ch} ch, {dtype}")
                    return dev, rate, ch, dtype
            except Exception as e:
                last_err = e
        raise RuntimeError(
            "No microphone could be opened. Check Settings > Privacy & security > "
            f"Microphone (desktop-app access). Last error: {last_err}")


class Resampler:
    """One responsibility: native capture blocks -> 16 kHz mono float32 frames."""

    def __init__(self, src_rate: int, dtype: str) -> None:
        self.step = src_rate / SAMPLE_RATE
        self.phase = 0.0
        self._buf: list[np.ndarray] = []
        self._buf_len = 0
        self._chan = 0
        self._probe: list[list[float]] | None = []   # per-channel RMS during first ~2 s
        self._scale = 1.0 / 32768.0 if dtype == "int16" else 1.0

    def push(self, block: np.ndarray) -> np.ndarray | None:
        """Return one 16 kHz mono frame of BLOCK samples when enough input exists."""
        x = block.astype(np.float32) * self._scale
        if x.ndim == 1:
            x = x[:, None]
        if self._probe is not None:                    # choose the loudest channel once
            self._probe.append([float(np.sqrt(np.mean(c**2))) for c in x.T])
            if len(self._probe) == 20:
                self._chan = int(np.argmax(np.mean(self._probe, axis=0)))
                self._probe = None
        col = x[:, self._chan]
        self._buf.append(col)
        self._buf_len += col.size

        need = int(np.ceil(self.phase + BLOCK * self.step)) + 1
        if self._buf_len < need:
            return None
        buf = np.concatenate(self._buf)
        pos = self.phase + np.arange(BLOCK + 1) * self.step
        out = np.interp(pos, np.arange(buf.size), buf)
        consumed = int(np.floor(pos[-1]))              # keep unconsumed tail, no audio lost
        self._buf = [buf[consumed:]]
        self._buf_len = buf.size - consumed
        self.phase = float(pos[-1] - consumed)
        return out[:BLOCK].astype(np.float32)


class MicStream:
    """One responsibility: stream fixed-size 16 kHz mono blocks from the microphone.

    Preferred backend is a PortAudio *callback* stream: blocks arrive on
    PortAudio's high-priority thread with no gaps (~100% of realtime audio).

    Some Windows WDM-KS devices accept a callback stream but never fire it, so
    the stream is verified by waiting for the first block. When that happens we
    fall back to repeated ``sd.rec`` bursts, which do work there but captured
    only ~67% of realtime audio on this laptop (measured).

    ``stats()`` exposes which backend is live plus coverage / dropped counts so
    the UI can prove the capture is healthy.
    """

    OPEN_TIMEOUT = 1.5

    def __init__(self, device: int | str | None = None, prefer: str = "callback") -> None:
        self._device = device
        self._prefer = prefer
        self._frames: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._raw: queue.Queue[np.ndarray] = queue.Queue(maxsize=256)
        self._stop = threading.Event()
        self._audio_seen = threading.Event()
        self._stream: sd.InputStream | None = None
        self._threads: list[threading.Thread] = []
        self._backend = "none"
        self._dropped = 0
        self._xruns = 0
        self._frame_count = 0
        self._started = time.perf_counter()

        self._dev, self._rate, self._ch, self._dtype = InputProber(device).find()
        self._rs = Resampler(self._rate, self._dtype)
        self.device_name = str(sd.query_devices(
            self._dev if self._dev is not None else sd.default.device[0])["name"])

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "MicStream":
        self._started = time.perf_counter()
        if self._prefer == "callback" and self._start_callback():
            return self
        self._start_burst()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._close_stream()
        for thread in self._threads:
            thread.join(timeout=1.5)

    def read(self, timeout: float = 0.2) -> np.ndarray | None:
        try:
            return self._frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def stats(self) -> dict[str, float | int | str]:
        elapsed = max(time.perf_counter() - self._started, 1e-6)
        return {
            "backend": self._backend,
            "device": self.device_name,
            "rate": self._rate,
            "frames": self._frame_count,
            "frames_per_sec": round(self._frame_count / elapsed, 2),
            "coverage": round(self._frame_count * BLOCK_DUR / elapsed, 3),
            "dropped": self._dropped,
            "xruns": self._xruns,
        }

    # -- backends ----------------------------------------------------------
    def _start_callback(self) -> bool:
        try:
            self._stream = sd.InputStream(
                samplerate=self._rate, channels=self._ch, dtype=self._dtype,
                device=self._dev, blocksize=0, latency="low",
                callback=self._on_audio)
            self._stream.start()
        except Exception as exc:
            print(f"[callback capture unavailable: {str(exc).splitlines()[0]}]", file=sys.stderr)
            self._close_stream()
            return False
        if self._audio_seen.wait(self.OPEN_TIMEOUT):
            self._backend = "callback"
            self._start_consumer()
            return True
        print("[callback stream accepted but silent -> falling back to bursts]", file=sys.stderr)
        self._close_stream()
        self._rs = Resampler(self._rate, self._dtype)
        return False

    def _start_burst(self) -> None:
        self._backend = "burst"
        self._threads = [
            threading.Thread(target=self._burst_loop, name="mic-burst", daemon=True),
            threading.Thread(target=self._consume_loop, name="mic-consume", daemon=True),
        ]
        for thread in self._threads:
            thread.start()

    def _start_consumer(self) -> None:
        self._threads = [threading.Thread(target=self._consume_loop,
                                          name="mic-consume", daemon=True)]
        self._threads[0].start()

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """PortAudio callback: copy and leave, never block for long."""
        if status:
            self._xruns += 1
        self._audio_seen.set()
        try:
            self._raw.put_nowait(indata.copy())
        except queue.Full:
            self._dropped += 1

    def _burst_loop(self) -> None:
        n = max(1, int(self._rate * BLOCK_DUR))
        while not self._stop.is_set():
            try:
                arr = sd.rec(n, samplerate=self._rate, channels=self._ch,
                             dtype=self._dtype, device=self._dev)
                sd.wait()
            except Exception as exc:
                print(f"[capture error: {str(exc).splitlines()[0]}]", file=sys.stderr)
                return
            if self._stop.is_set():
                return
            try:
                self._raw.put_nowait(arr)
            except queue.Full:
                self._dropped += 1

    def _consume_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._raw.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                mono = self._rs.push(raw)
            except Exception as exc:
                print(f"[resampler error: {str(exc).splitlines()[0]}]", file=sys.stderr)
                return
            if mono is None:
                continue
            self._frame_count += 1
            try:
                self._frames.put_nowait(mono)
            except queue.Full:
                self._dropped += 1

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass


