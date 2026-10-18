"""Database access for inventory. Only the service uses it."""

import uuid
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.inventory.models import (
    AppEnvironment,
    Application,
    Asset,
    AssetOwnership,
    DataCategory,
    DataElement,
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

    # --- Assets

    def _filtered_assets(
        self,
        query: str | None,
        domain_id: uuid.UUID | None,
        asset_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> Select[tuple[Asset]]:
        statement = select(Asset)
        if scope is not None:
            statement = statement.where(Asset.domain_id.in_(scope))
        if query:
            statement = statement.where(Asset.name.ilike(f"%{query}%"))
        if domain_id is not None:
            statement = statement.where(Asset.domain_id == domain_id)
        if asset_type is not None:
            statement = statement.where(Asset.type == asset_type)
        return statement

    def list_assets(
        self,
        *,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
        query: str | None,
        domain_id: uuid.UUID | None,
        asset_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> list[Asset]:
        """Ordered by (name, id), like applications."""
        statement = self._filtered_assets(query, domain_id, asset_type, scope).options(
            selectinload(Asset.ownerships)
        )
        if after is not None:
            name, after_id = after
            statement = statement.where(
                or_(Asset.name > name, (Asset.name == name) & (Asset.id > after_id))
            )
        return list(self._session.scalars(statement.order_by(Asset.name, Asset.id).limit(limit)))

    def count_assets(
        self,
        *,
        query: str | None,
        domain_id: uuid.UUID | None,
        asset_type: str | None,
        scope: frozenset[uuid.UUID] | None,
    ) -> int:
        subquery = self._filtered_assets(query, domain_id, asset_type, scope).subquery()
        return self._session.scalar(select(func.count()).select_from(subquery)) or 0

    def get_asset(self, asset_id: uuid.UUID) -> Asset | None:
        statement = (
            select(Asset)
            .where(Asset.id == asset_id)
            .options(selectinload(Asset.data_elements), selectinload(Asset.ownerships))
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(statement)

    def get_data_element(self, element_id: uuid.UUID) -> DataElement | None:
        return self._session.get(DataElement, element_id)

    def element_name_taken(
        self, asset_id: uuid.UUID, name: str, *, excluding: uuid.UUID | None = None
    ) -> bool:
        statement = select(DataElement.id).where(
            DataElement.asset_id == asset_id, func.lower(DataElement.name) == name.lower()
        )
        if excluding is not None:
            statement = statement.where(DataElement.id != excluding)
        return self._session.scalar(statement) is not None

    def pending_ownerships(self, user_id: uuid.UUID, scope: frozenset[uuid.UUID] | None):
        """Pending ownerships assigned to `user_id`, oldest first, with their assets."""
        statement = (
            select(AssetOwnership)
            .join(Asset, Asset.id == AssetOwnership.asset_id)
            .where(AssetOwnership.user_id == user_id, AssetOwnership.status == "pending")
            .order_by(AssetOwnership.assigned_at, AssetOwnership.id)
        )
        if scope is not None:
            statement = statement.where(Asset.domain_id.in_(scope))
        return list(self._session.scalars(statement))

    def add_asset_part[T: (Asset, DataElement, AssetOwnership)](self, entity: T) -> T:
        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def flush_asset_part(self, entity: Asset | DataElement | AssetOwnership) -> None:
        self._session.flush()
        self._session.refresh(entity)
