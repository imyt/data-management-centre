"""In-memory repository for the reference `example` resource (no database yet)."""

from datetime import UTC, datetime

from app.modules.examples.domain import Example, ExampleStatus

_SEED = [
    Example("EX-0001", "Customer master", ExampleStatus.ACTIVE, datetime(2026, 10, 1, tzinfo=UTC)),
    Example("EX-0002", "Payments ledger", ExampleStatus.DRAFT, datetime(2026, 10, 2, tzinfo=UTC)),
    Example("EX-0003", "Legacy CRM", ExampleStatus.RETIRED, datetime(2026, 10, 3, tzinfo=UTC)),
]


class InMemoryExampleRepository:
    def __init__(self, examples: list[Example] | None = None) -> None:
        source = _SEED if examples is None else examples
        self._examples = sorted(source, key=lambda example: example.id)

    async def list_after(self, after_id: str | None, limit: int) -> list[Example]:
        rows = [e for e in self._examples if after_id is None or e.id > after_id]
        return rows[:limit]

    async def count(self) -> int:
        return len(self._examples)

    async def get(self, example_id: str) -> Example | None:
        return next((e for e in self._examples if e.id == example_id), None)
