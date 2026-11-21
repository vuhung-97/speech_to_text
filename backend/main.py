"""HTTP composition root: settings -> engine -> pipeline -> FastAPI app.

The process bootstrap (CLI arguments, uvicorn, browser) lives in
``backend.bootstrap``. Tests import :func:`create_app` from here directly.

Run:  python run.py                (or: python -m backend.main)
      python run.py --mode accurate --no-browser
"""

from __future__ import annotations

import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .adapters.embedding.onnx_e5 import build_embedder
from .adapters.importer.docx_faq import parse_docx
from .adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                            SqliteFaqRepository)
from .adapters.retrieval.sqlite_faq_audio import SqliteFaqAudioRepository
from .adapters.storage.sqlite import (Database, SqliteAuditLog, SqliteQueryLog,
                                      SqliteSessionRepository)
from .adapters.storage.sqlite_faq_documents import SqliteFaqDocumentRepository
from .config.paths import DB_PATH, DIST_DIR, TTS_TEMP_DIR
from .config.settings import Settings
from .middleware import errors, request_log
from .ports.embedding import Embedder
from .routes import build_router
from .services.audio_sessions import AudioSessionHub
from .services.audio.temp_store import cleanup_stale_sessions
from .services.event_service import EventBus
from .services.faq_audio_service import FaqAudioService
from .services.faq_documents import FaqDocumentsService
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
    faq_audio_repo = SqliteFaqAudioRepository(database)
    faq_documents_repo = SqliteFaqDocumentRepository(database)
    faq_matcher = SqliteFaqMatcher(faq_repo, embedder)
    faq_service = FaqService(faq_repo, faq_matcher, embedder)
    app.state.embedder = embedder
    app.state.embed_note = embed_note
    app.state.faq_repo = faq_repo
    app.state.faq_matcher = faq_matcher
    app.state.faq_service = faq_service
    app.state.faq_documents = FaqDocumentsService(
        faq_documents_repo, faq_repo, faq_service, faq_matcher)
    app.state.outline_parser = parse_docx
    app.state.audit = SqliteAuditLog(database)
    app.state.faq_audio = FaqAudioService(faq_audio_repo, faq_repo, app.state.tts,
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


if __name__ == "__main__":
    from .bootstrap import main

    sys.exit(main())
