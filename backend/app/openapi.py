"""Renders the OpenAPI spec that is committed to contracts/openapi.json."""

import json

from app.core.config import Settings
from app.main import create_app


def render_openapi() -> str:
    spec = create_app(Settings(_env_file=None)).openapi()
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
