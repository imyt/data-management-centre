import json
import re
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI

from dmc_api.main import _require_operation_id
from dmc_api.openapi import render_openapi

CONTRACT = Path(__file__).resolve().parents[4] / "contracts" / "openapi.json"


def test_committed_contract_matches_the_app() -> None:
    assert CONTRACT.read_text(encoding="utf-8") == render_openapi(), (
        "contracts/openapi.json is out of date. Run `npm run api:sync` in frontend/."
    )


def test_operation_ids_are_unique_verb_resource() -> None:
    spec = json.loads(render_openapi())
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]

    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z]+[A-Z][A-Za-z]+", i) for i in ids)


def test_route_without_operation_id_is_rejected() -> None:
    router = APIRouter()

    @router.get("/anonymous")
    async def anonymous() -> None: ...

    app = FastAPI(generate_unique_id_function=_require_operation_id)
    with pytest.raises(RuntimeError, match="needs an explicit operation_id"):
        app.include_router(router)
        app.openapi()
