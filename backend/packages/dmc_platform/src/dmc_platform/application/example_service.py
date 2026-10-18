"""Business logic for the reference `example` resource."""

from typing import Protocol

from dmc_common.public import NotFoundError, PageResult, decode_cursor, encode_cursor
from dmc_platform.domain.example import Example


class ExampleRepository(Protocol):
    async def list_after(self, after_id: str | None, limit: int) -> list[Example]: ...
    async def count(self) -> int: ...
    async def get(self, example_id: str) -> Example | None: ...


class ExampleService:
    """Lists and reads examples, ordered by id. Shows the tier pattern; holds no real rules."""

    def __init__(self, repository: ExampleRepository) -> None:
        self._repository = repository

    async def list_examples(self, *, limit: int, cursor: str | None) -> PageResult[Example]:
        """Return up to `limit` examples after `cursor`, and a cursor for the next page if any."""
        after_id = decode_cursor(cursor) if cursor else None
        rows = await self._repository.list_after(after_id, limit + 1)
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1].id) if len(rows) > limit else None
        total = await self._repository.count()
        return PageResult(items=items, next_cursor=next_cursor, total=total)

    async def get_example(self, example_id: str) -> Example:
        """Return one example, or raise NotFoundError."""
        example = await self._repository.get(example_id)
        if example is None:
            raise NotFoundError(f"Example {example_id} does not exist.", details={"id": example_id})
        return example
