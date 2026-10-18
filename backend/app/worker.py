"""The worker's composition root and the `dmc-worker` command (ADR 0009).

    uv run dmc-worker

Runs until SIGINT or SIGTERM, then finishes the job in hand and exits; a second signal exits at
once (the job's lease then expires and another worker retries it). Like the API, it refuses to
start against a database that is not at the code's migration head.
"""

import argparse
import logging
import signal
import sys
import threading
from datetime import timedelta
from types import FrameType

from app.core.config import get_settings
from app.core.db import Database, create_database_engine
from app.core.jobs.housekeeping import register_platform_jobs
from app.core.jobs.registry import Registry
from app.core.jobs.worker import Worker
from app.core.logs import configure_logging
from app.core.migrations import DatabaseOutOfDateError, ensure_database_is_current
from app.modules.connectors import jobs as connectors
from app.modules.policy import jobs as policy

logger = logging.getLogger("app.worker")


def build_registry() -> Registry:
    """Every job, event handler and schedule. Modules add theirs here as they gain them."""
    registry = Registry()
    register_platform_jobs(registry)
    connectors.register(
        registry, interval=timedelta(seconds=get_settings().harvest_interval_seconds)
    )
    policy.register(registry)
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dmc-worker", description="Run background work.")
    parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level, settings.effective_log_format)
    if not settings.database_url:
        print("Set DMC_DATABASE_URL (see backend/.env.example).", file=sys.stderr)
        return 2

    engine = create_database_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            ensure_database_is_current(connection)
    except DatabaseOutOfDateError as exc:
        print(exc, file=sys.stderr)
        return 1

    stop = threading.Event()

    def request_stop(signum: int, _frame: FrameType | None) -> None:
        if stop.is_set():
            raise KeyboardInterrupt
        logger.info("%s received: stopping after the current work", signal.Signals(signum).name)
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    worker = Worker(
        Database(engine),
        build_registry(),
        lease=timedelta(seconds=settings.job_lease_seconds),
        poll_interval=settings.worker_poll_seconds,
    )
    try:
        worker.run(stop)
    except KeyboardInterrupt:
        logger.warning("Stopped without finishing the current work")
        return 130
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
