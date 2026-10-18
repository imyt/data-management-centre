"""Renders the OpenAPI spec that is committed to contracts/openapi.json."""

from app.core.config import Settings
from app.core.contract import render_spec
from app.main import create_app


def render_openapi() -> str:
    return render_spec(create_app(Settings(_env_file=None)).openapi())
