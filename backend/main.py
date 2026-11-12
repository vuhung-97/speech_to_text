"""Entry point: settings -> engine -> pipeline -> FastAPI app -> uvicorn.

Run:  python run.py                (or: python -m backend.main)
      python run.py --mode accurate --no-browser
"""

from __future__ import annotations

import argparse
import socket
import sys
import webbrowser
from contextlib import asynccontextmanager
from typing import Any

import sounddevice as sd
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config.paths import DIST_DIR, SAMPLES_DIR, SETTINGS_PATH
from .config.settings import Settings
from .middleware import errors
from .routes import build_router
from .services.engines import available_engines, create_engine
from .services.event_service import EventBus
from .services.replay_service import ReplayService
from .services.transcription_service import LivePipeline


def create_app(settings: Settings, pipeline: LivePipeline, replay: ReplayService,
               bus: EventBus, dist_dir=DIST_DIR) -> FastAPI:
    """Composition root for the HTTP layer (also used by the tests)."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        pipeline.start()
        try:
            yield
        finally:
            pipeline.stop()

    app = FastAPI(title="STT Trực Tiếp", version="2.0", docs_url="/api/docs",
                  redoc_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.pipeline = pipeline
    app.state.replay = replay
    app.state.bus = bus

    errors.register(app)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])  # dev server on :5173 proxies anyway
    app.include_router(build_router())

    index = dist_dir / "index.html"
    if index.is_file():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="web")
    else:
        @app.get("/", include_in_schema=False)
        def missing_build() -> dict[str, str]:
            return {"ok": False,
                    "error": "frontend chưa build - chạy: cd frontend && npm install && npm run build"}
    return app


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Offline Vietnamese STT with a web UI + API.")
    p.add_argument("--cpu-threads", type=int, default=None,
                   help="model CPU threads (default: settings.json -> 2)")
    p.add_argument("--mode", default=None, choices=("accurate", "realtime"),
                   help="accurate: one decode per sentence (default) | realtime: live draft")
    p.add_argument("--device", default=None, help="input device index or name")
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
    p.add_argument("--list-devices", action="store_true", help="list audio input devices")
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


def main() -> int:
    args = parse_args()
    if args.list_devices:
        print(sd.query_devices())
        return 0

    settings = Settings(args.settings, catalog=available_engines)
    settings.apply_cli({
        "cpu_threads": args.cpu_threads,
        "mode": args.mode,
        "device": args.device,
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
    app = create_app(settings, pipeline, replay, bus)

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


if __name__ == "__main__":
    sys.exit(main())
