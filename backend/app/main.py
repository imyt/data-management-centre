"""App factory. Mounts the core and module routers under /api/v1."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.core import health
from app.core.config import Settings, get_settings
from app.core.db import Database, create_database_engine
from app.core.handlers import REQUEST_ID_HEADER, RequestIdMiddleware, register_error_handlers
from app.modules.examples import router as examples

API_PREFIX = "/api/v1"


def _require_operation_id(route: APIRoute) -> str:
    """FastAPI calls this only for routes without an explicit operation_id: fail fast."""
    raise RuntimeError(f"{sorted(route.methods)} {route.path} needs an explicit operation_id")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)
    engine = create_database_engine(settings.database_url) if settings.database_url else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="DMC API",
        version=version("dmc-backend"),
        generate_unique_id_function=_require_operation_id,
        lifespan=lifespan,
    )
    app.state.database = Database(engine) if engine is not None else None
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(examples.router, prefix=API_PREFIX)
    return app


app = create_app()
