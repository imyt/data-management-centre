"""Liveness and readiness. Not a domain module: the API and, later, the worker each expose them."""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import Database
from app.core.schemas import error_responses

logger = logging.getLogger(__name__)


class HealthRead(BaseModel):
    status: Literal["ok"]


class HealthReadyRead(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


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


@router.get(
    "/health/ready",
    response_model=HealthReadyRead,
    status_code=status.HTTP_200_OK,
    operation_id="getHealthReady",
    summary="Readiness check: the API can reach its database",
    responses=error_responses(503),
)
def get_health_ready(request: Request) -> HealthReadyRead:
    database: Database | None = request.app.state.database
    if database is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No database is configured.")
    try:
        with database.transaction() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness check failed: database unreachable", exc_info=True)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "The database is not reachable."
        ) from None
    return HealthReadyRead(status="ok", database="ok")
