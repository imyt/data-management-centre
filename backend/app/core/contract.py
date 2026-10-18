"""The API contract: how the OpenAPI spec is serialized and hashed (ADR 0004 §5, ADR 0008).

`contracts/openapi.json` is exactly `render_spec(app.openapi())`, which CI checks. The frontend
build hashes that file and `GET /api/v1/meta` hashes the spec the API serves, both with
`contract_hash`, so equal hashes mean the bundle's client was generated from this API.
"""

import hashlib
import json
from typing import Any


def render_spec(spec: dict[str, Any]) -> str:
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def contract_hash(text: str) -> str:
    """`sha256:<hex>` of the UTF-8 text with LF line endings, whatever the checkout used."""
    normalized = text.replace("\r\n", "\n")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
