"""App factory. Mounts each package's routers under /api/v1."""

import logging
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from dmc_api.errors import REQUEST_ID_HEADER, RequestIdMiddleware, register_error_handlers
from dmc_api.settings import Settings, get_settings
from dmc_platform.api import examples, health

API_PREFIX = "/api/v1"


def _require_operation_id(route: APIRoute) -> str:
    """FastAPI calls this only for routes without an explicit operation_id: fail fast."""
    raise RuntimeError(f"{sorted(route.methods)} {route.path} needs an explicit operation_id")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="DMC API",
        version=version("dmc-api"),
        generate_unique_id_function=_require_operation_id,
    )
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
