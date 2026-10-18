"""Database access for evaluation. Only the service uses it. Results are only ever inserted."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased

from app.modules.evaluation.models import EvaluationResult, EvaluationRun


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Runs

    def add_run(self, trigger: str, requested_by: str | None) -> EvaluationRun:
        run = EvaluationRun(trigger=trigger, requested_by=requested_by)
        self._session.add(run)
        self._session.flush()
        self._session.refresh(run)
        return run

    def finish_run(self, run: EvaluationRun, counts: dict[str, int]) -> None:
        run.counts = counts
        run.finished_at = datetime.now(UTC)
        self._session.flush()

    # --- Results

    def lock_applied_control(self, applied_control_id: uuid.UUID) -> None:
        """Serialise evaluations of one applied control until the transaction ends, so two
        workers cannot both see 'no result yet' and both write one."""
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"evaluation:{applied_control_id}"},
        )

    def latest_for(self, applied_control_id: uuid.UUID) -> EvaluationResult | None:
        return self._session.scalar(
            select(EvaluationResult)
            .where(EvaluationResult.applied_control_id == applied_control_id)
            .order_by(EvaluationResult.id.desc())
            .limit(1)
        )

    def add_result(self, result: EvaluationResult) -> EvaluationResult:
        self._session.add(result)
        self._session.flush()
        self._session.refresh(result)
        return result

    def get(self, result_id: uuid.UUID) -> EvaluationResult | None:
        return self._session.get(EvaluationResult, result_id)

    def _filtered(
        self,
        *,
        applied_control_id: uuid.UUID | None,
        control_id: uuid.UUID | None,
        subject_type: str | None,
        subject_id: uuid.UUID | None,
        outcome: str | None,
        latest_only: bool,
        scope: frozenset[uuid.UUID] | None,
    ) -> tuple[Any, Select[Any]]:
        """The entity to select and a statement over it. With `latest_only`, one row per applied
        control: its most recent result."""
        model: Any = EvaluationResult
        statement = select(EvaluationResult)
        if latest_only:
            latest = (
                select(EvaluationResult)
                .ext(distinct_on(EvaluationResult.applied_control_id))
                .order_by(EvaluationResult.applied_control_id, EvaluationResult.id.desc())
                .subquery()
            )
            model = aliased(EvaluationResult, latest)
            statement = select(model)
        if applied_control_id is not None:
            statement = statement.where(model.applied_control_id == applied_control_id)
        if control_id is not None:
            statement = statement.where(model.control_id == control_id)
        if subject_type is not None:
            statement = statement.where(model.subject_type == subject_type)
        if subject_id is not None:
            statement = statement.where(model.subject_id == subject_id)
        if outcome is not None:
            statement = statement.where(model.outcome == outcome)
        if scope is not None:
            statement = statement.where(model.subject_domain_id.in_(scope))
        return model, statement

    def list_results(
        self, *, after: uuid.UUID | None, limit: int, **filters: Any
    ) -> list[EvaluationResult]:
        model, statement = self._filtered(**filters)
        if after is not None:
            statement = statement.where(model.id < after)
        return list(self._session.scalars(statement.order_by(model.id.desc()).limit(limit)))

    def count_results(self, **filters: Any) -> int:
        _, statement = self._filtered(**filters)
        return self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
