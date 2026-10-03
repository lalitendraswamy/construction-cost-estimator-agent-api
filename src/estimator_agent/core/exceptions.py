"""Domain exceptions + FastAPI handlers that render them as RFC 9457 problem details."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from estimator_agent.core.logging import get_logger

log = get_logger(__name__)


class EstimatorError(Exception):
    """Base for all expected, domain-level errors."""

    status_code: int = 400
    title: str = "Bad request"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(EstimatorError):
    status_code = 404
    title = "Not found"


class ConflictError(EstimatorError):
    status_code = 409
    title = "Conflict"


class SpecIncompleteError(EstimatorError):
    """Raised if anything tries to price a ProjectSpec that still has missing fields."""

    status_code = 422
    title = "Project spec incomplete"


class RatesUnavailableError(EstimatorError):
    status_code = 503
    title = "Rates unavailable"


class NotConfiguredError(EstimatorError):
    status_code = 501
    title = "Not configured"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EstimatorError)
    async def _domain(request: Request, exc: EstimatorError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": exc.title,
                "status": exc.status_code,
                "detail": exc.detail,
                "instance": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            media_type="application/problem+json",
            content={"type": "about:blank", "title": "Internal error", "status": 500},
        )
