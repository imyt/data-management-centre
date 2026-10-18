from datetime import UTC, datetime

import pytest

from app.core.errors import InvalidInputError, NotFoundError
from app.modules.examples.domain import Example, ExampleStatus
from app.modules.examples.repository import InMemoryExampleRepository
from app.modules.examples.service import ExampleService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_example(example_id: str) -> Example:
    return Example(example_id, f"Example {example_id}", ExampleStatus.ACTIVE, datetime.now(UTC))


def make_service(*ids: str) -> ExampleService:
    return ExampleService(InMemoryExampleRepository([make_example(i) for i in ids]))


@pytest.mark.anyio
async def test_pages_follow_the_cursor_until_exhausted() -> None:
    service = make_service("C", "A", "B")

    first = await service.list_examples(limit=2, cursor=None)
    second = await service.list_examples(limit=2, cursor=first.next_cursor)

    assert [e.id for e in first.items] == ["A", "B"]
    assert [e.id for e in second.items] == ["C"]
    assert second.next_cursor is None
    assert first.total == 3


@pytest.mark.anyio
async def test_exact_page_has_no_next_cursor() -> None:
    page = await make_service("A", "B").list_examples(limit=2, cursor=None)

    assert page.next_cursor is None


@pytest.mark.anyio
async def test_empty_repository_returns_empty_page() -> None:
    page = await make_service().list_examples(limit=10, cursor=None)

    assert page.items == []
    assert page.total == 0


@pytest.mark.anyio
async def test_bad_cursor_is_invalid_input() -> None:
    with pytest.raises(InvalidInputError):
        await make_service("A").list_examples(limit=1, cursor="%%%")


@pytest.mark.anyio
async def test_missing_example_raises_not_found() -> None:
    with pytest.raises(NotFoundError):
        await make_service("A").get_example("Z")
