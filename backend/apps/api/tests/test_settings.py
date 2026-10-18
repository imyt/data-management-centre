import pytest

from dmc_api.settings import Settings


def test_cors_origins_are_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMC_CORS_ORIGINS", "http://a.test, http://b.test,")

    assert Settings(_env_file=None).cors_origins == ["http://a.test", "http://b.test"]


def test_defaults_need_no_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.cors_origins == []
