"""Pairing check (ADR 0004 §5). The frontend compares `contract` with the hash it was built with."""

import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.core.config import Environment, Settings
from app.core.contract import contract_hash, render_spec


class MetaRead(BaseModel):
    environment: Environment
    version: str = Field(examples=["0.1.0"])
    commit: str = Field(
        description="Short git SHA of the build, or `unknown`.", examples=["24a18c3"]
    )
    contract: str = Field(
        description="`sha256:<hex>` of the OpenAPI contract this API serves.",
        examples=["sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"],
    )


router = APIRouter(tags=["platform"])


@lru_cache
def _git_commit() -> str:
    """Local fallback when DMC_COMMIT is unset: the checkout's HEAD, if git is there."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def resolve_commit(configured: str | None) -> str:
    return configured or _git_commit()


def _served_contract(request: Request) -> str:
    state = request.app.state
    if getattr(state, "contract", None) is None:
        state.contract = contract_hash(render_spec(request.app.openapi()))
    return state.contract


@router.get(
    "/meta",
    response_model=MetaRead,
    status_code=status.HTTP_200_OK,
    operation_id="getMeta",
    summary="Environment, build and contract hash",
)
async def get_meta(request: Request) -> MetaRead:
    settings: Settings = request.app.state.settings
    return MetaRead(
        environment=settings.environment,
        version=request.app.version,
        commit=resolve_commit(settings.commit),
        contract=_served_contract(request),
    )
