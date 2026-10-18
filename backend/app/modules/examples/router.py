"""Reference resource for the scaffold. Copy its shape for real resources, then delete it."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.schemas import error_responses
from app.modules.examples.repository import InMemoryExampleRepository
from app.modules.examples.schemas import ExamplePage, ExampleRead
from app.modules.examples.service import ExampleService

router = APIRouter(prefix="/examples", tags=["examples"])

_service = ExampleService(InMemoryExampleRepository())


def get_example_service() -> ExampleService:
    return _service


Service = Annotated[ExampleService, Depends(get_example_service)]


@router.get(
    "",
    response_model=ExamplePage,
    status_code=status.HTTP_200_OK,
    operation_id="listExamples",
    summary="List examples",
    responses=error_responses(400, 422),
)
async def list_examples(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> ExamplePage:
    page = await service.list_examples(limit=limit, cursor=cursor)
    return ExamplePage(
        items=[ExampleRead.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
        total=page.total,
    )


@router.get(
    "/{example_id}",
    response_model=ExampleRead,
    status_code=status.HTTP_200_OK,
    operation_id="getExample",
    summary="Get an example",
    responses=error_responses(404, 422),
)
async def get_example(example_id: str, service: Service) -> ExampleRead:
    return ExampleRead.model_validate(await service.get_example(example_id))
