"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from estimator_agent import __version__
from estimator_agent.api import health
from estimator_agent.api import v1 as api_v1
from estimator_agent.api.container import ContainerFactory, default_container
from estimator_agent.api.middleware import RequestContextMiddleware
from estimator_agent.api.rate_limit import limiter
from estimator_agent.core.config import Settings, get_settings
from estimator_agent.core.exceptions import register_exception_handlers
from estimator_agent.core.logging import configure_logging, get_logger

log = get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    container_factory: ContainerFactory = default_container,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with container_factory(settings) as container:
            app.state.container = container
            log.info("startup", env=settings.app_env, version=__version__)
            yield
        log.info("shutdown")

    app = FastAPI(
        title="Construction Estimator Agent API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.router)
    app.include_router(api_v1.router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("estimator_agent.main:app", host="0.0.0.0", port=8000)  # noqa: S104
