"""Database access for inventory. Only the service uses it."""

import uuid
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.inventory.models import (
    AppEnvironment,
    Application,
    DataCategory,
    DataStore,
    Domain,
    Purpose,
    Region,
    RetentionPolicy,
)

type ReferenceModel = (
    type[Domain] | type[DataCategory] | type[Region] | type[RetentionPolicy] | type[Purpose]
)


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Reference data

    def list_reference(self, model: ReferenceModel) -> list[Any]:
        return list(self._session.scalars(select(model).order_by(model.name)))

    def reference_exists(self, model: ReferenceModel, item_id: uuid.UUID) -> bool:
        return self._session.get(model, item_id) is not None

    # --- Applications

    def _filtered(
        self,
        query: str | None,
        domain_id: uuid.UUID | None,
        lifecycle_status: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> Select[Application]:
        statement = select(Application)
        if scope is not None:
            statement = statement.where(Application.domain_id.in_(scope))
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(Application.name.ilike(pattern), Application.code.ilike(pattern))
            )
        if domain_id is not None:
            statement = statement.where(Application.domain_id == domain_id)
        if lifecycle_status is not None:
            statement = statement.where(Application.lifecycle_status == lifecycle_status)
        return statement

    def list_applications(
        self,
        *,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
        query: str | None,
        domain_id: uuid.UUID | None,
        lifecycle_status: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> list[Application]:
        """Ordered by (name, id) so the keyset cursor is stable when names repeat.

        `scope` limits rows to those domains; None means every domain.
        """
        statement = self._filtered(query, domain_id, lifecycle_status, scope)
        if after is not None:
            name, after_id = after
            statement = statement.where(
                or_(
                    Application.name > name,
                    (Application.name == name) & (Application.id > after_id),
                )
            )
        statement = statement.order_by(Application.name, Application.id).limit(limit)
        return list(self._session.scalars(statement))

    def count_applications(
        self,
        *,
        query: str | None,
        domain_id: uuid.UUID | None,
        lifecycle_status: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> int:
        subquery = self._filtered(query, domain_id, lifecycle_status, scope).subquery()
        return self._session.scalar(select(func.count()).select_from(subquery)) or 0

    def get_application(self, application_id: uuid.UUID) -> Application | None:
        statement = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.environments).selectinload(AppEnvironment.data_stores)
            )
            # Refresh collections already loaded earlier in this session (e.g. before an add).
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(statement)

    def code_taken(self, code: str, *, excluding: uuid.UUID | None = None) -> bool:
        statement = select(Application.id).where(func.lower(Application.code) == code.lower())
        if excluding is not None:
            statement = statement.where(Application.id != excluding)
        return self._session.scalar(statement) is not None

    def get_environment(self, environment_id: uuid.UUID) -> AppEnvironment | None:
        return self._session.get(AppEnvironment, environment_id)

    def add[T: (Application, AppEnvironment, DataStore)](self, entity: T) -> T:
        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def flush(self, entity: Application) -> None:
        self._session.flush()
        self._session.refresh(entity)
