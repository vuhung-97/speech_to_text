"""Request context: one id per call, one structured line per API request.

The id is echoed in ``X-Request-ID`` so a UI error can be matched to a log line.
Only ``/api`` paths are logged; SSE heartbeats would otherwise flood the log.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("stt_binh.http")


def register(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("rid=%s %s %s -> 500", request_id,
                             request.method, request.url.path)
            raise
        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api") and request.url.path != "/api/state":
            logger.info("rid=%s %s %s %s %.0fms", request_id, request.method,
                        request.url.path, response.status_code, elapsed)
        elif request.url.path == "/api/state":
            logger.debug("rid=%s GET /api/state %.0fms", request_id, elapsed)
        return response
