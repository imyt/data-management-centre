"""Reference entity for the scaffold. Delete with the rest of `example` later."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExampleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class Example:
    id: str
    name: str
    status: ExampleStatus
    created_at: datetime
