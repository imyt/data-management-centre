"""Value sets for connectors. Stored as text with a check constraint, not Postgres enums."""

from enum import StrEnum


class SnapshotStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ObjectKind(StrEnum):
    """What a physical object is. Only tables and columns map to assets and data elements."""

    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"


def check_in(column: str, values: type[StrEnum]) -> str:
    """SQL for a check constraint that keeps `column` within an enum's values."""
    quoted = ", ".join(f"'{v.value}'" for v in values)
    return f"{column} IN ({quoted})"
