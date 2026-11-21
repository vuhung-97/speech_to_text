"""Exception middleware: every failure becomes a JSON ``{ok, error}`` response.

Client mistakes keep their message (``ApiError``/``ValueError``). Unexpected
failures are logged with the traceback and answered with a generic message so
internal paths, SQL and stack details never leak to the browser.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..utils.errors import ApiError

logger = logging.getLogger("stt_binh.http")

INTERNAL_ERROR_TEXT = "máy chủ gặp lỗi không mong muốn"


def register(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"ok": False, "error": exc.message},
                            status_code=exc.status_code)

    @app.exception_handler(FileNotFoundError)
    async def _not_found(request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"ok": False, "error": INTERNAL_ERROR_TEXT},
                            status_code=500)


__all__ = ["INTERNAL_ERROR_TEXT", "register"]
