"""Exception middleware: every failure becomes a JSON ``{ok, error}`` response."""

from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..utils.errors import ApiError


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
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        return JSONResponse({"ok": False, "error": str(exc) or exc.__class__.__name__},
                            status_code=500)
