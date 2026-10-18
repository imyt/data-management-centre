"""Database access for audit events."""

from collections.abc import Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent

# One lock key for the whole chain: pg_advisory_xact_lock holds it until the writer's transaction
# ends, so concurrent writers append one after another and the chain never forks.
CHAIN_LOCK_KEY = 0x646D635F61756469  # "dmc_audi"


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_chain(self) -> None:
        self._session.execute(select(func.pg_advisory_xact_lock(CHAIN_LOCK_KEY)))

    def last_hash(self) -> str | None:
        return self._session.scalar(
            select(AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1)
        )

    def add(self, event: AuditEvent) -> AuditEvent:
        self._session.add(event)
        self._session.flush()
        return event

    def in_chain_order(self, batch_size: int = 1000) -> Iterator[AuditEvent]:
        query = select(AuditEvent).order_by(AuditEvent.seq).execution_options(yield_per=batch_size)
        yield from self._session.scalars(query)
