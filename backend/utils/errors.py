"""Domain errors that controllers may raise (translated to JSON by middleware)."""

from __future__ import annotations


class ApiError(Exception):
    """A client-visible error with an HTTP status."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
