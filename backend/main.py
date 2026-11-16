"""Entry point: settings -> engine -> pipeline -> FastAPI app -> uvicorn.

Run:  python run.py                (or: python -m backend.main)
      python run.py --mode accurate --no-browser
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .adapters.embedding.onnx_e5 import build_embedder
from .adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                            SqliteFaqRepository)
from .adapters.storage.sqlite import (Database, SqliteAuditLog, SqliteQueryLog,
                                      SqliteSessionRepository)
from .config.paths import DB_PATH, DIST_DIR, SAMPLES_DIR, SETTINGS_PATH, TTS_TEMP_DIR
from .config.settings import Settings
from .middleware import errors, request_log
from .ports.embedding import Embedder
from .routes import build_router
from .services.audio_sessions import AudioSessionHub
from .services.audio.temp_store import cleanup_stale_sessions
from .services.engines import available_engines, create_engine
from .services.event_service import EventBus
from .services.faq_audio_service import FaqAudioService
from .services.faq_service import FaqService
from .services.qa_service import QaService
from .services.replay_service import ReplayService
from .services.transcription_service import LivePipeline
from .services.tts_service import TtsService
from .utils.errors import ApiError


def _mount_spa(app: FastAPI, dist_dir: Path, index: Path) -> None:
    """Serve the built SPA with working deep links.

    ``StaticFiles(html=True)`` answers 404 for ``/sessions/abc`` because no such
    file exists. A single-page app must return ``index.html`` for every non-API
    path and let the client router resolve it.
    """
    assets = dist_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    root = dist_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:
        if path == "api" or path.startswith(("api/", "events")):
            raise ApiError("không tìm thấy", status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(root / "index.html")


def create_app(settings: Settings, pipeline: LivePipeline, replay: ReplayService,
               bus: EventBus, dist_dir=DIST_DIR, *,
               tts: TtsService | None = None,
               db_path: str | Path | None = None,
               qa: QaService | None = None,
               embedder: Embedder | None = None,
               audio_cache_dir: str | Path | None = None) -> FastAPI:
    """Composition root for the HTTP layer (also used by the tests)."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        cleanup_stale_sessions(TTS_TEMP_DIR)
        # The browser owns the microphone: the server pipeline is a recognition
        # engine only (replay + settings), no capture threads are started.
        pause = getattr(pipeline, "set_paused", None)
        if callable(pause):
            pause(True)
        try:
            yield
        finally:
            stop = getattr(pipeline, "stop", None)
            if callable(stop):
                stop()
            speech = getattr(_app.state, "tts", None)
            shutdown = getattr(speech, "shutdown", None)
            if callable(shutdown):
                shutdown()

    app = FastAPI(title="STT Trực Tiếp", version="2.0", docs_url="/api/docs",
                  redoc_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.pipeline = pipeline
    app.state.replay = replay
    app.state.bus = bus
    app.state.tts = tts or TtsService()

    database = Database(db_path or DB_PATH)
    sessions_repo = SqliteSessionRepository(database)
    query_log = SqliteQueryLog(database)
    app.state.db = database
    app.state.sessions = sessions_repo
    app.state.query_log = query_log

    if embedder is None:
        embedder, embed_note = build_embedder()
    else:
        embed_note = ""
    faq_repo = SqliteFaqRepository(database)
    faq_matcher = SqliteFaqMatcher(faq_repo, embedder)
    faq_service = FaqService(faq_repo, faq_matcher, embedder)
    app.state.embedder = embedder
    app.state.embed_note = embed_note
    app.state.faq_repo = faq_repo
    app.state.faq_matcher = faq_matcher
    app.state.faq_service = faq_service
    app.state.audit = SqliteAuditLog(database)
    app.state.faq_audio = FaqAudioService(faq_repo, app.state.tts,
                                         cache_dir=audio_cache_dir)
    app.state.qa = qa or QaService(faq_matcher, sessions_repo, query_log)

    # One ONNX engine, one lock: browser sessions share it and take turns.
    app.state.transcribe_lock = threading.Lock()
    app.state.audio_hub = AudioSessionHub(
        engine_provider=lambda: getattr(app.state.pipeline, "engine", None),
        settings_provider=lambda: getattr(app.state.pipeline, "settings", None),
        transcribe_lock=app.state.transcribe_lock,
    )

    errors.register(app)
    request_log.register(app)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])  # dev server on :5173 proxies anyway
    app.include_router(build_router())

    index = dist_dir / "index.html"
    if index.is_file():
        _mount_spa(app, dist_dir, index)
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


def main() -> int:
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


if __name__ == "__main__":
    sys.exit(main())
