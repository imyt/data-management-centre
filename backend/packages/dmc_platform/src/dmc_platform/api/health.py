from fastapi import APIRouter, status

from dmc_platform.schemas import HealthRead

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
