"""The `evaluation` schema: runs, and the append-only results they write."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDv7PrimaryKey
from app.modules.evaluation.domain import Outcome, Trigger

SCHEMA = "evaluation"


def check_in(column: str, values: type[Outcome] | type[Trigger]) -> str:
    quoted = ", ".join(f"'{v.value}'" for v in values)
    return f"{column} IN ({quoted})"


class EvaluationRun(UUIDv7PrimaryKey, Base):
    """One pass of the engine over some applied controls, and why it ran."""

    __tablename__ = "evaluation_run"
    __table_args__ = (
        CheckConstraint(check_in("trigger", Trigger), name="trigger"),
        {"schema": SCHEMA},
    )

    trigger: Mapped[str] = mapped_column(Text)
    # Who asked (an actor) for an on-demand run; null for events and schedules.
    requested_by: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # How many applied controls were looked at, and how many results of each outcome were written.
    counts: Mapped[dict[str, int]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class EvaluationResult(UUIDv7PrimaryKey, Base):
    """What one rule said about one subject, from the facts it was given. Never updated or
    deleted (a trigger refuses both): a new evaluation writes a new row."""

    __tablename__ = "evaluation_result"
    __table_args__ = (
        CheckConstraint(check_in("outcome", Outcome), name="outcome"),
        CheckConstraint("stale_after > evaluated_at", name="stale_after_later"),
        Index("ix_evaluation_result_applied_control", "applied_control_id", "id"),
        Index("ix_evaluation_result_subject", "subject_type", "subject_id"),
        {"schema": SCHEMA},
    )

    # What ran. Applied controls, controls and rule versions belong to policy: ids only.
    applied_control_id: Mapped[uuid.UUID]
    control_id: Mapped[uuid.UUID]
    control_code: Mapped[str] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(Text)
    rule_version_id: Mapped[uuid.UUID]
    rule_version: Mapped[int] = mapped_column(Integer)
    # What was checked; the domain is a copy, so reads can be scoped without asking inventory.
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID]
    subject_name: Mapped[str] = mapped_column(Text)
    subject_domain_id: Mapped[uuid.UUID] = mapped_column(index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.evaluation_run.id"))
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    stale_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(Text)
    measured: Mapped[Decimal | None] = mapped_column(Numeric)
    threshold: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    # The facts the verdict rests on, and their hash: the same facts under the same rule version
    # are never judged twice in a row.
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fact_hash: Mapped[str] = mapped_column(Text)
    # The result before this one for the applied control, and how the outcome moved.
    previous_result_id: Mapped[uuid.UUID | None]
    transition: Mapped[str] = mapped_column(Text)
