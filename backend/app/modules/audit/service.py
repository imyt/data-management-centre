"""Public interface of the audit module: the only file other modules import.

Every write in DMC calls `AuditService(session).record(...)` with the session that makes the
change, so the change and its audit event commit or roll back together.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError
from app.modules.audit.domain import GENESIS_HASH, EventContent, to_json_value
from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository


@dataclass(frozen=True)
class RecordedEvent:
    id: uuid.UUID
    seq: int
    hash: str


@dataclass(frozen=True)
class ChainCheck:
    """Result of re-hashing the whole chain. `broken_at` is the first event that doesn't match."""

    valid: bool
    checked: int
    broken_at: uuid.UUID | None = None
    problem: str | None = None


class AuditService:
    def __init__(self, session: Session) -> None:
        self._repository = AuditRepository(session)

    def record(
        self,
        *,
        actor: str,
        action: str,
        subject_type: str,
        subject_id: str | uuid.UUID,
        reason: str | None = None,
        before: Any = None,
        after: Any = None,
        reason_required: bool = False,
    ) -> RecordedEvent:
        """Append an event to the chain in the caller's transaction.

        Pass `reason_required=True` for risk decisions (accept risk, approve an exception, access
        or a transfer): they are refused without a reason (FR-C8).
        """
        reason = reason.strip() if reason else None
        if reason_required and not reason:
            raise InvalidInputError(
                f"A reason is required for {action}.", details={"field": "reason"}
            )

        self._repository.lock_chain()
        content = EventContent(
            at=datetime.now(UTC),
            actor=actor,
            action=action,
            subject_type=subject_type,
            subject_id=str(subject_id),
            reason=reason,
            before=to_json_value(before),
            after=to_json_value(after),
            prev_hash=self._repository.last_hash() or GENESIS_HASH,
        )
        event = self._repository.add(AuditEvent(**vars(content), hash=content.digest()))
        return RecordedEvent(id=event.id, seq=event.seq, hash=event.hash)

    def verify_chain(self) -> ChainCheck:
        """Re-hash every event in order; any edited, removed or reordered event breaks the chain."""
        expected_prev = GENESIS_HASH
        checked = 0
        for event in self._repository.in_chain_order():
            content = EventContent(
                at=event.at,
                actor=event.actor,
                action=event.action,
                subject_type=event.subject_type,
                subject_id=event.subject_id,
                reason=event.reason,
                before=event.before,
                after=event.after,
                prev_hash=event.prev_hash,
            )
            if event.prev_hash != expected_prev:
                return ChainCheck(False, checked, event.id, "does not follow the previous event")
            if content.digest() != event.hash:
                return ChainCheck(False, checked, event.id, "content does not match its hash")
            expected_prev = event.hash
            checked += 1
        return ChainCheck(True, checked)
