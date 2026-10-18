"""Runtime settings, read from DMC_* environment variables (and backend/.env when present)."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "dev", "staging", "production"]

# Deployed environments must be fully configured at start-up (ADR 0004 §6).
DEPLOYED: frozenset[Environment] = frozenset({"dev", "staging", "production"})
# Dev authentication, seed data and debug payloads are refused here (ADR 0004 §6).
PROTECTED: frozenset[Environment] = frozenset({"staging", "production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DMC_", env_file=".env", extra="ignore")

    environment: Environment = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Unset: plain text in local, JSON lines everywhere else (ARCHITECTURE.md §12).
    log_format: Literal["json", "plain"] | None = None
    cors_origins: Annotated[list[str], NoDecode] = []
    # SQLAlchemy URLs, e.g. postgresql+psycopg://dmc_app:…@localhost:5432/dmc
    database_url: str | None = None
    migration_database_url: str | None = None
    # The estate sample database, as the role that owns it; only dmc-seed uses it (ADR 0004 §8).
    estate_migration_url: str | None = None
    # dev: a persona named in the X-DMC-Dev-User header (ADR 0007). oidc: bearer tokens (Phase 4).
    auth_mode: Literal["dev", "oidc"] = "dev"
    # The git SHA this build came from, reported by GET /api/v1/meta. Unset: asks git, if present.
    commit: str | None = None
    # Worker (dmc-worker): seconds between polls when idle, and how long a job's lease lasts
    # without a refresh before another worker treats its worker as dead and requeues it.
    worker_poll_seconds: float = 1.0
    job_lease_seconds: int = 300
    # How often the worker harvests every data store (a store is also harvested when registered
    # and on demand).
    harvest_interval_seconds: int = 86_400
    # How often the worker evaluates every applied control (events and requests evaluate sooner).
    evaluation_interval_seconds: int = 21_600

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def effective_log_format(self) -> Literal["json", "plain"]:
        if self.log_format:
            return self.log_format
        return "plain" if self.environment == "local" else "json"

    @model_validator(mode="after")
    def _deployed_needs_a_database(self) -> Self:
        if self.environment in DEPLOYED and not self.database_url:
            raise ValueError(f"DMC_DATABASE_URL is required in the {self.environment} environment")
        return self

    @model_validator(mode="after")
    def _no_dev_auth_when_protected(self) -> Self:
        if self.environment in PROTECTED and self.auth_mode == "dev":
            raise ValueError(
                f"DMC_AUTH_MODE=dev is not allowed in the {self.environment} environment"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
