"""Liveness endpoint. Not a domain module: the API and, later, the worker each expose one."""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel


class HealthRead(BaseModel):
    status: Literal["ok"]


router = APIRouter(tags=["platform"])


@router.get(
    "/health",
    response_model=HealthRead,
    status_code=status.HTTP_200_OK,
    operation_id="getHealth",
    summary="Liveness check",
)
async def get_health() -> HealthRead:
    return HealthRead(status="ok")
