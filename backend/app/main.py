"""App factory. Mounts the core and module routers under /api/v1."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.core import health, meta
from app.core.auth import configure_authentication
from app.core.config import Settings, get_settings
from app.core.db import Database, create_database_engine
from app.core.handlers import REQUEST_ID_HEADER, RequestIdMiddleware, register_error_handlers
from app.core.jobs import router as jobs
from app.core.logs import AccessLogMiddleware, configure_logging
from app.core.migrations import ensure_database_is_current
from app.modules.connectors import router as connectors
from app.modules.examples import router as examples
from app.modules.identity import router as identity
from app.modules.identity.service import IdentityDirectory
from app.modules.inventory import router as inventory
from app.modules.workflow import router as workflow

API_PREFIX = "/api/v1"


def _require_operation_id(route: APIRoute) -> str:
    """FastAPI calls this only for routes without an explicit operation_id: fail fast."""
    raise RuntimeError(f"{sorted(route.methods or ())} {route.path} needs an explicit operation_id")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.effective_log_format)
    engine = create_database_engine(settings.database_url) if settings.database_url else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if engine is not None:
            with engine.connect() as connection:
                ensure_database_is_current(connection)
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="DMC API",
        version=version("dmc-backend"),
        generate_unique_id_function=_require_operation_id,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = Database(engine) if engine is not None else None
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    # Added last, so outermost: the request ID is bound before the access log is written.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    configure_authentication(app, settings, IdentityDirectory())

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(meta.router, prefix=API_PREFIX)
    app.include_router(jobs.router, prefix=API_PREFIX)
    app.include_router(examples.router, prefix=API_PREFIX)
    app.include_router(identity.router, prefix=API_PREFIX)
    app.include_router(inventory.router, prefix=API_PREFIX)
    app.include_router(connectors.router, prefix=API_PREFIX)
    app.include_router(workflow.router, prefix=API_PREFIX)
    return app


app = create_app()
