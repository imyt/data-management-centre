import pytest

from app.core.config import Settings


def test_cors_origins_are_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMC_CORS_ORIGINS", "http://a.test, http://b.test,")

    assert Settings(_env_file=None).cors_origins == ["http://a.test", "http://b.test"]


def test_defaults_need_no_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.cors_origins == []


@pytest.mark.parametrize("environment", ["dev", "staging", "production"])
def test_deployed_environments_require_a_database(environment: str) -> None:
    with pytest.raises(ValueError, match="DMC_DATABASE_URL is required"):
        Settings(_env_file=None, environment=environment)  # type: ignore[arg-type]
