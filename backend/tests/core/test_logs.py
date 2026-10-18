import json
import logging

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logs import JsonFormatter, PlainFormatter, current_log_context, log_context
from app.main import create_app


def _json_lines(text: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def _record(message: str = "hello", **extra: object) -> logging.LogRecord:
    record = logging.makeLogRecord({"name": "dmc.test", "levelname": "INFO", "msg": message})
    record.__dict__.update(extra)
    return record


def test_log_context_nests_and_resets() -> None:
    with log_context(job_id="job-1"):
        with log_context(request_id="req-1"):
            assert current_log_context() == {"job_id": "job-1", "request_id": "req-1"}
        assert current_log_context() == {"job_id": "job-1"}
    assert current_log_context() == {}


def test_json_record_is_one_line_with_context_and_extras() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record(exc_info=__import__("sys").exc_info(), attempt=2)
    with log_context(job_id="job-7"):
        line = JsonFormatter().format(record)

    entry = json.loads(line)
    assert "\n" not in line
    assert entry["message"] == "hello"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "dmc.test"
    assert entry["job_id"] == "job-7"
    assert entry["attempt"] == 2
    assert "ValueError: boom" in entry["exception"]


def test_plain_record_appends_context() -> None:
    with log_context(request_id="req-9"):
        line = PlainFormatter().format(_record())

    assert line.endswith("dmc.test  hello  request_id=req-9")


@pytest.mark.parametrize(
    ("environment", "log_format", "expected"),
    [
        ("local", None, "plain"),
        ("local", "json", "json"),
        ("test", None, "json"),
        ("dev", "plain", "plain"),
    ],
)
def test_log_format_defaults_by_environment(
    environment: str, log_format: str | None, expected: str
) -> None:
    settings = Settings(
        _env_file=None,
        environment=environment,  # type: ignore[arg-type]
        log_format=log_format,  # type: ignore[arg-type]
        database_url="postgresql+psycopg://x@localhost/x",
    )

    assert settings.effective_log_format == expected


def _json_client() -> TestClient:
    app = create_app(Settings(_env_file=None, environment="test", log_format="json"))
    router = APIRouter()

    @router.get("/boom", operation_id="getBoom")
    async def boom() -> None:
        logging.getLogger("dmc.test").info("about to fail")
        raise RuntimeError("secret")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_access_log_per_request_carries_the_request_id(capsys: pytest.CaptureFixture[str]) -> None:
    _json_client().get("/api/v1/health", headers={"X-Request-ID": "req-abc"})

    access = [e for e in _json_lines(capsys.readouterr().out) if e["logger"] == "dmc.access"]
    assert len(access) == 1
    assert access[0]["request_id"] == "req-abc"
    assert access[0]["method"] == "GET"
    assert access[0]["path"] == "/api/v1/health"
    assert access[0]["status"] == 200
    assert isinstance(access[0]["duration_ms"], float)


def test_failed_request_logs_with_its_request_id(capsys: pytest.CaptureFixture[str]) -> None:
    _json_client().get("/boom", headers={"X-Request-ID": "req-500"})

    entries = _json_lines(capsys.readouterr().out)
    by_logger = {e["logger"]: e for e in entries}
    assert by_logger["dmc.test"]["request_id"] == "req-500"
    assert by_logger["app.core.handlers"]["request_id"] == "req-500"
    assert "secret" in str(by_logger["app.core.handlers"]["exception"])
    assert by_logger["dmc.access"]["status"] == 500
    assert by_logger["dmc.access"]["request_id"] == "req-500"
