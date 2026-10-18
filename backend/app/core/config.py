"""Runtime settings, read from DMC_* environment variables (and backend/.env when present)."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "dev", "staging", "production"]

# Deployed environments must be fully configured at start-up (ADR 0004 §6).
DEPLOYED: frozenset[Environment] = frozenset({"dev", "staging", "production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DMC_", env_file=".env", extra="ignore")

    environment: Environment = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = []
    # SQLAlchemy URLs, e.g. postgresql+psycopg://dmc_app:…@localhost:5432/dmc
    database_url: str | None = None
    migration_database_url: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _deployed_needs_a_database(self) -> Self:
        if self.environment in DEPLOYED and not self.database_url:
            raise ValueError(f"DMC_DATABASE_URL is required in the {self.environment} environment")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
