"""Structured logs (ARCHITECTURE.md §12): one JSON object per line, or plain text locally.

Every record carries the fields bound with `log_context`: the request ID for API requests
(bound by `RequestIdMiddleware`) and, for background work, the job ID:

    with log_context(job_id=str(job.id)):
        run(job)

Fields passed with `extra=` on a single call are added to that record only.
"""

import json
import logging
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Literal

from starlette.types import ASGIApp, Message, Receive, Scope, Send

LogFormat = Literal["json", "plain"]

_context: ContextVar[Mapping[str, str]] = ContextVar(
    "dmc_log_context", default=MappingProxyType({})
)

# Attributes every LogRecord has; anything else on a record came from `extra=`. Uvicorn adds
# `color_message`, a copy of the message with terminal colours.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}

# Uvicorn's own handlers are replaced so its records use our format; its access log is replaced
# by AccessLogMiddleware, which knows the request ID.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

access_logger = logging.getLogger("dmc.access")


@contextmanager
def log_context(**fields: str) -> Iterator[None]:
    """Adds fields to every log record written inside the block, in this task or thread."""
    token = _context.set(MappingProxyType({**_context.get(), **fields}))
    try:
        yield
    finally:
        _context.reset(token)


def current_log_context() -> Mapping[str, str]:
    return _context.get()


def _fields(record: logging.LogRecord) -> dict[str, Any]:
    extra = {k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS}
    return {**_context.get(), **extra}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_fields(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """For a terminal: time, level, logger, message, then the context fields as key=value."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-7s %(name)s  %(message)s", "%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        fields = " ".join(f"{k}={v}" for k, v in _fields(record).items())
        if not fields:
            return line
        head, newline, rest = line.partition("\n")
        return f"{head}  {fields}{newline}{rest}"


class _StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever sys.stdout is now, so a replaced stdout (pytest's capture) still works."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def configure_logging(level: str, log_format: LogFormat) -> None:
    """Sends every record, uvicorn's included, to stdout in the chosen format.

    Safe to call more than once: it replaces only the handler it installed before.
    """
    handler = _StdoutHandler()
    handler.setFormatter(JsonFormatter() if log_format == "json" else PlainFormatter())
    root = logging.getLogger()
    for previous in [h for h in root.handlers if isinstance(h, _StdoutHandler)]:
        root.removeHandler(previous)
    root.addHandler(handler)
    root.setLevel(level)
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


class AccessLogMiddleware:
    """One record per request: method, path, status and duration in milliseconds."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500  # until the app starts a response; an exception that escapes is a 500

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            method, path = scope["method"], scope["path"]
            access_logger.info(
                "%s %s %s %.1fms",
                method,
                path,
                status,
                duration_ms,
                extra={
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": duration_ms,
                },
            )
