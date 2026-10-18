"""How an audit event is hashed. Pure functions: the service and chain verification share them."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class EventContent:
    """Everything an event's hash covers, including the hash of the event before it."""

    at: datetime
    actor: str
    action: str
    subject_type: str
    subject_id: str
    reason: str | None
    before: Any
    after: Any
    prev_hash: str

    def digest(self) -> str:
        canonical = {
            "at": self.at.astimezone(UTC).isoformat(),
            "actor": self.actor,
            "action": self.action,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "reason": self.reason,
            "before": self.before,
            "after": self.after,
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(_canonical_json(canonical).encode()).hexdigest()


def to_json_value(value: Any) -> Any:
    """Plain JSON (UUIDs, datetimes, decimals as strings), so what is stored is what is hashed."""
    return None if value is None else json.loads(json.dumps(value, default=str))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
