"""Value sets for inventory entities. Stored as text with a check constraint, not Postgres enums."""

from enum import StrEnum


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Hosting(StrEnum):
    ON_PREMISES = "on_premises"
    PRIVATE_CLOUD = "private_cloud"
    PUBLIC_CLOUD = "public_cloud"
    SAAS = "saas"


class LifecycleStatus(StrEnum):
    """ARCHITECTURE §6.4: planned → active → retiring → decommissioned."""

    PLANNED = "planned"
    ACTIVE = "active"
    RETIRING = "retiring"
    DECOMMISSIONED = "decommissioned"


class EnvironmentType(StrEnum):
    PRODUCTION = "production"
    NON_PRODUCTION = "non_production"


class DataStoreType(StrEnum):
    RELATIONAL = "relational"
    DOCUMENT = "document"
    OBJECT_STORAGE = "object_storage"
    WAREHOUSE = "warehouse"
    FILE_SHARE = "file_share"


class HarvestStatus(StrEnum):
    """`never` until the first harvest runs (slice 4)."""

    NEVER = "never"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def check_in(column: str, values: type[StrEnum]) -> str:
    """SQL for a check constraint that keeps `column` within an enum's values."""
    quoted = ", ".join(f"'{v.value}'" for v in values)
    return f"{column} IN ({quoted})"
