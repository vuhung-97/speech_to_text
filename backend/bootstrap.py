"""Process bootstrap: CLI arguments, model loading, port probe and uvicorn.

The HTTP composition root lives in :mod:`backend.main`; this module only knows
how to start one process around it. Tests import ``create_app`` directly and
never touch this file.
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import webbrowser
from typing import Any

import uvicorn

from .config.paths import SAMPLES_DIR, SETTINGS_PATH
from .config.settings import Settings
from .main import create_app
from .services.engines import available_engines, create_engine
from .services.event_service import EventBus
from .services.replay_service import ReplayService
from .services.transcription_service import LivePipeline
from .services.tts_service import TtsService


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Offline Vietnamese STT with a web UI + API.")
    p.add_argument("--cpu-threads", type=int, default=None,
                   help="model CPU threads (default: settings.json -> 2)")
    p.add_argument("--mode", default=None, choices=("accurate", "realtime"),
                   help="accurate: one decode per sentence (default) | realtime: live draft")
    p.add_argument("--silence-hang", type=float, default=None,
                   help="seconds of silence that close a sentence")
    p.add_argument("--threshold", type=float, default=None,
                   help="absolute RMS speech floor")
    p.add_argument("--decode-interval", type=float, default=None,
                   help="seconds between draft decodes (realtime mode only)")
    p.add_argument("--host", default="127.0.0.1", help="bind address")
    p.add_argument("--port", type=int, default=8765, help="HTTP port")
    p.add_argument("--settings", default=str(SETTINGS_PATH),
                   help="settings file (default: settings.json in the project root)")
    p.add_argument("--no-browser", action="store_true", help="do not open the browser")
    p.add_argument("--no-tts-preload", action="store_true",
                   help="không nạp trước model VieNeu vào RAM khi khởi động")
    return p.parse_args()


def free_port(preferred: int, span: int = 10) -> int:
    for port in range(preferred, preferred + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # NOTE: SO_REUSEADDR on Windows lets us bind a port that is already
            # in use, which would defeat this probe - so don't set it here.
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"no free port in {preferred}..{preferred + span - 1}")


def _load_engine(settings: Settings) -> Any:
    values = settings.values()
    try:
        return create_engine(str(values["model"]), values)
    except Exception as exc:
        fallback = next((key for key, spec in available_engines().items() if spec.available),
                        None)
        if fallback is None:
            raise RuntimeError(f"không có model nào dùng được: {exc}") from exc
        print(f"! {exc} -> dùng '{fallback}' cho phiên này")
        settings.apply_cli({"model": fallback})
        return create_engine(fallback, settings.values())


def _configure_console() -> None:
    """Keep Vietnamese help/log text readable on the Windows console."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _configure_console()
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    settings = Settings(args.settings, catalog=available_engines)
    settings.apply_cli({
        "cpu_threads": args.cpu_threads,
        "mode": args.mode,
        "silence_hang": args.silence_hang,
        "threshold": args.threshold,
        "decode_interval": args.decode_interval,
    })
    values = settings.values()
    print(f"Mode: {values['mode']} | model: {values['model']} | "
          f"threads: {values['cpu_threads']}")

    print("Loading model...")
    engine = _load_engine(settings)
    bus = EventBus()
    pipeline = LivePipeline(engine, bus, settings)
    replay = ReplayService(pipeline.decode, settings, SAMPLES_DIR)

    tts = TtsService()
    if not args.no_tts_preload:
        print("Preloading TTS model (VieNeu)...")
        tts.preload_async(synthesize=os.environ.get("TTS_PRELOAD_INFER") == "1")
    app = create_app(settings, pipeline, replay, bus, tts=tts)

    port = free_port(args.port)
    url = f"http://{args.host}:{port}/"
    print(f"UI ready at {url}  (Ctrl+C to stop)")
    print("API docs: /api/docs · settings: gear icon (Ctrl+Comma)")
    if not args.no_browser:
        webbrowser.open(url)

    try:
        uvicorn.run(app, host=args.host, port=port, log_level="warning")
    except KeyboardInterrupt:
        print("\nStopping...")
    return 0


__all__ = ["free_port", "main", "parse_args"]
