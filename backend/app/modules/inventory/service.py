"""Public interface of the inventory module: the only file other modules import.

Every write checks the caller's role and domain scope, then records an audit event in the same
session, so the change and its event commit together (ADR 0006).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import Permission, Principal, Role, allowed_actions, require
from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.pagination import PageResult, decode_cursor, encode_cursor
from app.modules.audit.service import AuditService
from app.modules.identity.service import IdentityService, User
from app.modules.inventory.domain import (
    AssetType,
    LifecycleStatus,
    OwnershipRole,
    OwnershipStatus,
)
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
from app.modules.inventory.repository import InventoryRepository, ReferenceModel
from app.modules.inventory.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    AssetCreate,
    AssetUpdate,
    DataElementCreate,
    DataElementUpdate,
    DataStoreCreate,
    EnvironmentCreate,
)

# Who may register and change applications (PRD §2). Changes also need the domain in scope.
_REGISTRARS = {Role.APPLICATION_OWNER, Role.GOVERNANCE}
CREATE_APPLICATION = Permission("create", _REGISTRARS)
EDIT_APPLICATION = Permission("edit", _REGISTRARS)
ADD_ENVIRONMENT = Permission("add_environment", _REGISTRARS)
ADD_DATA_STORE = Permission("add_data_store", _REGISTRARS)
_APPLICATION_PERMISSIONS = (EDIT_APPLICATION, ADD_ENVIRONMENT, ADD_DATA_STORE)

# Each lifecycle state may move only to the next one (ARCHITECTURE §6.4). Decommissioning needs
# every asset disposed of with evidence, which arrives with slice 28, so it is not offered yet.
_NEXT_LIFECYCLE = {
    LifecycleStatus.PLANNED: {LifecycleStatus.ACTIVE},
    LifecycleStatus.ACTIVE: {LifecycleStatus.RETIRING},
    LifecycleStatus.RETIRING: set(),
    LifecycleStatus.DECOMMISSIONED: set(),
}

REFERENCE_MODELS: dict[str, ReferenceModel] = {
    "domain": Domain,
    "data_category": DataCategory,
    "region": Region,
    "retention_policy": RetentionPolicy,
    "purpose": Purpose,
}


def application_list_actions(principal: Principal) -> list[str]:
    """`allowed_actions` on the applications list."""
    return allowed_actions(principal, [CREATE_APPLICATION])


def application_actions(principal: Principal, application: Application) -> list[str]:
    """`allowed_actions` on one application, from the same rules the writes check."""
    return allowed_actions(principal, _APPLICATION_PERMISSIONS, application.domain_id)


def _application_snapshot(application: Application) -> dict[str, Any]:
    return {
        "name": application.name,
        "code": application.code,
        "description": application.description,
        "domain_id": application.domain_id,
        "criticality": application.criticality,
        "hosting": application.hosting,
        "lifecycle_status": application.lifecycle_status,
        "app_owner_id": application.app_owner_id,
        "tech_owner_id": application.tech_owner_id,
    }


class InventoryService:
    def __init__(self, session: Session) -> None:
        self._repository = InventoryRepository(session)
        self._audit = AuditService(session)

    # --- Reference data

    def list_reference(self, kind: str) -> list[Any]:
        return self._repository.list_reference(REFERENCE_MODELS[kind])

    # --- Applications

    def list_applications(
        self,
        principal: Principal,
        *,
        limit: int,
        cursor: str | None,
        query: str | None = None,
        domain_id: uuid.UUID | None = None,
        lifecycle_status: LifecycleStatus | None = None,
    ) -> PageResult[Application]:
        """A page of the applications in the caller's domains, ordered by name."""
        after = self._decode_application_cursor(cursor) if cursor else None
        query = query.strip() if query else None
        status = lifecycle_status.value if lifecycle_status else None
        rows = self._repository.list_applications(
            after=after,
            limit=limit + 1,
            query=query,
            domain_id=domain_id,
            lifecycle_status=status,
            scope=principal.domain_ids,
        )
        items = rows[:limit]
        next_cursor = (
            encode_cursor(f"{items[-1].id}|{items[-1].name}") if len(rows) > limit else None
        )
        total = self._repository.count_applications(
            query=query, domain_id=domain_id, lifecycle_status=status, scope=principal.domain_ids
        )
        return PageResult(items=items, next_cursor=next_cursor, total=total)

    def get_application(self, principal: Principal, application_id: uuid.UUID) -> Application:
        """One application with its environments and stores, if it is in the caller's scope."""
        application = self._get(application_id)
        if not principal.in_scope(application.domain_id):
            raise PermissionDeniedError(
                "This application is outside the domains you are scoped to.",
                details={"id": str(application_id)},
            )
        return application

    def _get(self, application_id: uuid.UUID) -> Application:
        application = self._repository.get_application(application_id)
        if application is None:
            raise NotFoundError(
                f"Application {application_id} does not exist.",
                details={"id": str(application_id)},
            )
        return application

    def create_application(self, principal: Principal, data: ApplicationCreate) -> Application:
        require(principal, CREATE_APPLICATION, data.domain_id)
        if data.lifecycle_status not in (LifecycleStatus.PLANNED, LifecycleStatus.ACTIVE):
            raise InvalidInputError(
                "A new application starts as planned or active.",
                details={"field": "lifecycle_status"},
            )
        self._require_domain(data.domain_id)
        self._require_unique_code(data.code)
        application = self._repository.add(Application(**data.model_dump()))
        self._audit.record(
            actor=principal.actor,
            action="application.created",
            subject_type="application",
            subject_id=application.id,
            after=_application_snapshot(application),
        )
        return self._get(application.id)

    def update_application(
        self, principal: Principal, application_id: uuid.UUID, data: ApplicationUpdate
    ) -> Application:
        application = self._get(application_id)
        require(principal, EDIT_APPLICATION, application.domain_id)
        changes = data.model_dump(exclude_unset=True)
        for required in ("name", "code", "domain_id", "criticality", "hosting", "lifecycle_status"):
            if required in changes and changes[required] is None:
                raise InvalidInputError(f"{required} cannot be empty.", details={"field": required})
        if "domain_id" in changes:
            # Moving an application needs the target domain in scope too.
            require(principal, EDIT_APPLICATION, changes["domain_id"])
            self._require_domain(changes["domain_id"])
        if "code" in changes:
            self._require_unique_code(changes["code"], excluding=application.id)
        if "lifecycle_status" in changes:
            self._require_lifecycle_move(application, changes["lifecycle_status"])

        before = _application_snapshot(application)
        for field, value in changes.items():
            setattr(application, field, value)
        after = _application_snapshot(application)
        if after == before:
            return application
        self._repository.flush(application)
        changed = sorted(k for k in after if after[k] != before[k])
        self._audit.record(
            actor=principal.actor,
            action="application.updated",
            subject_type="application",
            subject_id=application.id,
            before={k: before[k] for k in changed},
            after={k: after[k] for k in changed},
        )
        return self._get(application.id)

    def add_environment(
        self, principal: Principal, application_id: uuid.UUID, data: EnvironmentCreate
    ) -> AppEnvironment:
        application = self._get(application_id)
        require(principal, ADD_ENVIRONMENT, application.domain_id)
        self._require_region(data.region_id)
        environment = self._repository.add(
            AppEnvironment(application_id=application.id, **data.model_dump())
        )
        self._audit.record(
            actor=principal.actor,
            action="app_environment.created",
            subject_type="application",
            subject_id=application.id,
            after={"environment_id": environment.id, **data.model_dump()},
        )
        return environment

    def add_data_store(
        self, principal: Principal, environment_id: uuid.UUID, data: DataStoreCreate
    ) -> DataStore:
        environment = self._repository.get_environment(environment_id)
        if environment is None:
            raise NotFoundError(
                f"Environment {environment_id} does not exist.",
                details={"id": str(environment_id)},
            )
        require(principal, ADD_DATA_STORE, environment.application.domain_id)
        self._require_region(data.region_id)
        store = self._repository.add(DataStore(environment_id=environment.id, **data.model_dump()))
        self._audit.record(
            actor=principal.actor,
            action="data_store.created",
            subject_type="application",
            subject_id=environment.application_id,
            after={
                "data_store_id": store.id,
                "environment_id": environment.id,
                **data.model_dump(),
            },
        )
        return store

    # --- Checks

    def _decode_application_cursor(self, cursor: str) -> tuple[str, uuid.UUID]:
        key, _, name = decode_cursor(cursor).partition("|")
        try:
            return name, uuid.UUID(key)
        except ValueError as exc:
            raise InvalidInputError("The cursor is not valid.", details={"cursor": cursor}) from exc

    def _require_domain(self, domain_id: uuid.UUID) -> None:
        if not self._repository.reference_exists(Domain, domain_id):
            raise InvalidInputError("Choose a domain that exists.", details={"field": "domain_id"})

    def _require_region(self, region_id: uuid.UUID) -> None:
        if not self._repository.reference_exists(Region, region_id):
            raise InvalidInputError("Choose a region that exists.", details={"field": "region_id"})

    def _require_unique_code(self, code: str, *, excluding: uuid.UUID | None = None) -> None:
        if self._repository.code_taken(code, excluding=excluding):
            raise ConflictError(
                f"Another application already uses the code {code}.", details={"field": "code"}
            )

    def _require_lifecycle_move(self, application: Application, target: LifecycleStatus) -> None:
        current = LifecycleStatus(application.lifecycle_status)
        if target != current and target not in _NEXT_LIFECYCLE[current]:
            raise InvalidInputError(
                f"An application cannot move from {current} to {target}.",
                details={"field": "lifecycle_status"},
            )


# --- Assets, data elements and ownership (FR-K5, FR-K6, FR-K10) ----------------------------------

# Application Owners declare datasets (PRD §2); Data Owners and Governance may too.
_DECLARERS = {Role.APPLICATION_OWNER, Role.DATA_OWNER, Role.GOVERNANCE}
CREATE_ASSET = Permission("create", _DECLARERS)
EDIT_ASSET = Permission("edit", _DECLARERS)
EDIT_ELEMENTS = Permission("edit_elements", _DECLARERS)
FLAG_CDE = Permission("flag_cde", {Role.DATA_OWNER, Role.GOVERNANCE})
ASSIGN_OWNER = Permission("assign_owner", _DECLARERS)
ASSIGN_STEWARD = Permission("assign_steward", {Role.DATA_OWNER, Role.GOVERNANCE})
_ASSET_PERMISSIONS = (EDIT_ASSET, EDIT_ELEMENTS, FLAG_CDE, ASSIGN_OWNER, ASSIGN_STEWARD)

_ASSIGN = {OwnershipRole.OWNER: ASSIGN_OWNER, OwnershipRole.STEWARD: ASSIGN_STEWARD}
# The role a user must hold to be named for each accountability.
_ASSIGNEE_ROLE = {OwnershipRole.OWNER: Role.DATA_OWNER, OwnershipRole.STEWARD: Role.DATA_STEWARD}

# How long an assignee has to confirm before the item is overdue in their Inbox.
CONFIRMATION_PERIOD = timedelta(days=14)


@dataclass(frozen=True)
class AssetView:
    """An asset with the users its ownership rows refer to, resolved through identity."""

    asset: Asset
    users: dict[uuid.UUID, User]


@dataclass(frozen=True)
class OwnershipDue:
    """One Inbox item: an ownership the current user has been asked to confirm."""

    ownership_id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    role: OwnershipRole
    assigned_by: str | None
    assigned_at: datetime
    due_at: datetime


def asset_list_actions(principal: Principal) -> list[str]:
    return allowed_actions(principal, [CREATE_ASSET])


def asset_actions(principal: Principal, asset: Asset) -> list[str]:
    """`allowed_actions` on one asset. Confirm and dispute are for the person it is assigned to."""
    actions = set(allowed_actions(principal, _ASSET_PERMISSIONS, asset.domain_id))
    if principal.in_scope(asset.domain_id):
        for ownership in asset.ownerships:
            if ownership.user_id != principal.user_id:
                continue
            if ownership.status == OwnershipStatus.PENDING:
                actions.add(f"confirm_{ownership.role}")
            if ownership.status != OwnershipStatus.DISPUTED:
                actions.add(f"dispute_{ownership.role}")
    return sorted(actions)


def _asset_snapshot(asset: Asset) -> dict[str, Any]:
    return {
        "name": asset.name,
        "type": asset.type,
        "description": asset.description,
        "domain_id": asset.domain_id,
        "data_category_id": asset.data_category_id,
        "business_context": asset.business_context,
        "is_stored": asset.is_stored,
        "retention_policy_id": asset.retention_policy_id,
    }


def _element_snapshot(element: DataElement) -> dict[str, Any]:
    return {
        "name": element.name,
        "data_type": element.data_type,
        "is_pii": element.is_pii,
        "pii_source": element.pii_source,
        "is_cde": element.is_cde,
    }


def _ownership_snapshot(ownership: AssetOwnership) -> dict[str, Any]:
    return {
        "role": ownership.role,
        "user_id": ownership.user_id,
        "status": ownership.status,
        "reason": ownership.reason,
    }


def _decode_name_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    key, _, name = decode_cursor(cursor).partition("|")
    try:
        return name, uuid.UUID(key)
    except ValueError as exc:
        raise InvalidInputError("The cursor is not valid.", details={"cursor": cursor}) from exc


class AssetService:
    def __init__(self, session: Session) -> None:
        self._repository = InventoryRepository(session)
        self._audit = AuditService(session)
        self._identity = IdentityService(session)

    # --- Reads

    def list_assets(
        self,
        principal: Principal,
        *,
        limit: int,
        cursor: str | None,
        query: str | None = None,
        domain_id: uuid.UUID | None = None,
        asset_type: AssetType | None = None,
    ) -> PageResult[AssetView]:
        """A page of the assets in the caller's domains, ordered by name."""
        after = _decode_name_cursor(cursor) if cursor else None
        query = query.strip() if query else None
        kind = asset_type.value if asset_type else None
        rows = self._repository.list_assets(
            after=after,
            limit=limit + 1,
            query=query,
            domain_id=domain_id,
            asset_type=kind,
            scope=principal.domain_ids,
        )
        items = rows[:limit]
        next_cursor = (
            encode_cursor(f"{items[-1].id}|{items[-1].name}") if len(rows) > limit else None
        )
        total = self._repository.count_assets(
            query=query, domain_id=domain_id, asset_type=kind, scope=principal.domain_ids
        )
        return PageResult(items=self._views(items), next_cursor=next_cursor, total=total)

    def _views(self, assets: list[Asset]) -> list[AssetView]:
        ids = {o.user_id for a in assets for o in a.ownerships}
        ids |= {o.assigned_by_id for a in assets for o in a.ownerships}
        users = self._identity.get_users(ids)
        return [AssetView(asset, users) for asset in assets]

    def get_asset(self, principal: Principal, asset_id: uuid.UUID) -> AssetView:
        """One asset with its data elements and ownership, if it is in the caller's scope."""
        asset = self._get(asset_id)
        if not principal.in_scope(asset.domain_id):
            raise PermissionDeniedError(
                "This asset is outside the domains you are scoped to.",
                details={"id": str(asset_id)},
            )
        return self._views([asset])[0]

    def _get(self, asset_id: uuid.UUID) -> Asset:
        asset = self._repository.get_asset(asset_id)
        if asset is None:
            raise NotFoundError(f"Asset {asset_id} does not exist.", details={"id": str(asset_id)})
        return asset

    # --- Declaring assets

    def create_asset(self, principal: Principal, data: AssetCreate) -> AssetView:
        require(principal, CREATE_ASSET, data.domain_id)
        self._check_declaration(
            data.domain_id, data.data_category_id, data.is_stored, data.retention_policy_id
        )
        asset = self._repository.add_asset_part(Asset(**data.model_dump()))
        self._audit.record(
            actor=principal.actor,
            action="asset.created",
            subject_type="asset",
            subject_id=asset.id,
            after=_asset_snapshot(asset),
        )
        return self.get_asset(principal, asset.id)

    def update_asset(
        self, principal: Principal, asset_id: uuid.UUID, data: AssetUpdate
    ) -> AssetView:
        asset = self._get(asset_id)
        require(principal, EDIT_ASSET, asset.domain_id)
        changes = data.model_dump(exclude_unset=True)
        for required in ("name", "type", "domain_id", "is_stored"):
            if required in changes and changes[required] is None:
                raise InvalidInputError(f"{required} cannot be empty.", details={"field": required})
        if changes.get("is_stored") is False and "retention_policy_id" not in changes:
            changes["retention_policy_id"] = None
        if "domain_id" in changes:
            # Moving an asset needs the target domain in scope too.
            require(principal, EDIT_ASSET, changes["domain_id"])
        before = _asset_snapshot(asset)
        merged = {**before, **changes}
        self._check_declaration(
            merged["domain_id"],
            merged["data_category_id"],
            merged["is_stored"],
            merged["retention_policy_id"],
        )
        for field, value in changes.items():
            setattr(asset, field, value)
        after = _asset_snapshot(asset)
        if after != before:
            self._repository.flush_asset_part(asset)
            changed = sorted(k for k in after if after[k] != before[k])
            self._audit.record(
                actor=principal.actor,
                action="asset.updated",
                subject_type="asset",
                subject_id=asset.id,
                before={k: before[k] for k in changed},
                after={k: after[k] for k in changed},
            )
        return self.get_asset(principal, asset.id)

    def _check_declaration(
        self,
        domain_id: uuid.UUID,
        data_category_id: uuid.UUID | None,
        is_stored: bool,
        retention_policy_id: uuid.UUID | None,
    ) -> None:
        if not self._repository.reference_exists(Domain, domain_id):
            raise InvalidInputError("Choose a domain that exists.", details={"field": "domain_id"})
        if data_category_id is not None and not self._repository.reference_exists(
            DataCategory, data_category_id
        ):
            raise InvalidInputError(
                "Choose a data category that exists.", details={"field": "data_category_id"}
            )
        if is_stored and retention_policy_id is None:
            raise InvalidInputError(
                "A stored asset needs a retention policy.",
                details={"field": "retention_policy_id"},
            )
        if not is_stored and retention_policy_id is not None:
            raise InvalidInputError(
                "Only a stored asset has a retention policy.",
                details={"field": "retention_policy_id"},
            )
        if retention_policy_id is not None and not self._repository.reference_exists(
            RetentionPolicy, retention_policy_id
        ):
            raise InvalidInputError(
                "Choose a retention policy that exists.", details={"field": "retention_policy_id"}
            )

    # --- Data elements

    def add_data_element(
        self, principal: Principal, asset_id: uuid.UUID, data: DataElementCreate
    ) -> DataElement:
        asset = self._get(asset_id)
        require(principal, EDIT_ELEMENTS, asset.domain_id)
        if data.is_cde:
            require(principal, FLAG_CDE, asset.domain_id)
        self._require_unique_element(asset.id, data.name)
        element = self._repository.add_asset_part(
            DataElement(
                asset_id=asset.id,
                name=data.name,
                data_type=data.data_type,
                is_pii=data.is_pii,
                pii_source="declared" if data.is_pii else None,
                is_cde=data.is_cde,
            )
        )
        self._audit.record(
            actor=principal.actor,
            action="data_element.created",
            subject_type="asset",
            subject_id=asset.id,
            after={"data_element_id": element.id, **_element_snapshot(element)},
        )
        return element

    def update_data_element(
        self, principal: Principal, element_id: uuid.UUID, data: DataElementUpdate
    ) -> DataElement:
        element = self._repository.get_data_element(element_id)
        if element is None:
            raise NotFoundError(
                f"Data element {element_id} does not exist.", details={"id": str(element_id)}
            )
        domain_id = element.asset.domain_id
        require(principal, EDIT_ELEMENTS, domain_id)
        changes = data.model_dump(exclude_unset=True)
        for required in ("name", "data_type", "is_pii", "is_cde"):
            if required in changes and changes[required] is None:
                raise InvalidInputError(f"{required} cannot be empty.", details={"field": required})
        if "is_cde" in changes and changes["is_cde"] != element.is_cde:
            require(principal, FLAG_CDE, domain_id)
        if "name" in changes:
            self._require_unique_element(element.asset_id, changes["name"], excluding=element.id)
        before = _element_snapshot(element)
        for field, value in changes.items():
            setattr(element, field, value)
        if element.is_pii and element.pii_source is None:
            element.pii_source = "declared"
        elif not element.is_pii:
            element.pii_source = None
        after = _element_snapshot(element)
        if after == before:
            return element
        self._repository.flush_asset_part(element)
        changed = sorted(k for k in after if after[k] != before[k])
        self._audit.record(
            actor=principal.actor,
            action="data_element.updated",
            subject_type="asset",
            subject_id=element.asset_id,
            before={"data_element_id": element.id, **{k: before[k] for k in changed}},
            after={"data_element_id": element.id, **{k: after[k] for k in changed}},
        )
        return element

    def _require_unique_element(
        self, asset_id: uuid.UUID, name: str, *, excluding: uuid.UUID | None = None
    ) -> None:
        if self._repository.element_name_taken(asset_id, name, excluding=excluding):
            raise ConflictError(
                f"This asset already has a data element called {name}.", details={"field": "name"}
            )

    # --- Ownership (FR-K10)

    def assign(
        self,
        principal: Principal,
        asset_id: uuid.UUID,
        role: OwnershipRole,
        user_id: uuid.UUID,
        reason: str | None,
    ) -> AssetView:
        """Name the Data Owner or Data Steward, or replace them. Replacing needs a reason."""
        asset = self._get(asset_id)
        require(principal, _ASSIGN[role], asset.domain_id)
        assignee = self._identity.get_users({user_id}).get(user_id)
        if assignee is None or _ASSIGNEE_ROLE[role] not in assignee.roles:
            raise InvalidInputError(
                f"Choose a user who is a {_ASSIGNEE_ROLE[role].value.replace('_', ' ')}.",
                details={"field": "user_id"},
            )
        if assignee.domain_ids is not None and asset.domain_id not in assignee.domain_ids:
            raise InvalidInputError(
                "That user is not scoped to this asset's domain.", details={"field": "user_id"}
            )
        current = next((o for o in asset.ownerships if o.role == role), None)
        if current is not None and not (reason and reason.strip()):
            raise InvalidInputError(
                "A reason is required to replace an assignment.", details={"field": "reason"}
            )
        if current is None:
            ownership = self._repository.add_asset_part(
                AssetOwnership(
                    asset_id=asset.id,
                    role=role.value,
                    user_id=user_id,
                    assigned_by_id=principal.user_id,
                )
            )
            self._audit.record(
                actor=principal.actor,
                action=f"asset.{role}_assigned",
                subject_type="asset",
                subject_id=asset.id,
                reason=reason,
                after=_ownership_snapshot(ownership),
            )
            return self.get_asset(principal, asset.id)
        if current.user_id == user_id:
            raise InvalidInputError(
                "That user already holds this assignment.", details={"field": "user_id"}
            )
        before = _ownership_snapshot(current)
        current.user_id = user_id
        current.status = OwnershipStatus.PENDING.value
        current.assigned_by_id = principal.user_id
        current.assigned_at = datetime.now().astimezone()
        current.decided_at = None
        current.reason = reason.strip() if reason else None
        # Refuses without a reason, which rolls the whole request back.
        self._audit.record(
            actor=principal.actor,
            action=f"asset.{role}_reassigned",
            subject_type="asset",
            subject_id=asset.id,
            reason=reason,
            before=before,
            after=_ownership_snapshot(current),
            reason_required=True,
        )
        self._repository.flush_asset_part(current)
        return self.get_asset(principal, asset.id)

    def confirm(self, principal: Principal, asset_id: uuid.UUID, role: OwnershipRole) -> AssetView:
        asset = self._get(asset_id)
        ownership = self._own_assignment(principal, asset, role)
        if ownership.status != OwnershipStatus.PENDING:
            raise ConflictError(
                "Only a pending assignment can be confirmed.", details={"status": ownership.status}
            )
        before = _ownership_snapshot(ownership)
        ownership.status = OwnershipStatus.CONFIRMED.value
        ownership.decided_at = datetime.now().astimezone()
        ownership.reason = None
        self._repository.flush_asset_part(ownership)
        self._audit.record(
            actor=principal.actor,
            action=f"asset.{role}_confirmed",
            subject_type="asset",
            subject_id=asset.id,
            before=before,
            after=_ownership_snapshot(ownership),
        )
        return self.get_asset(principal, asset.id)

    def dispute(
        self, principal: Principal, asset_id: uuid.UUID, role: OwnershipRole, reason: str
    ) -> AssetView:
        asset = self._get(asset_id)
        ownership = self._own_assignment(principal, asset, role)
        if ownership.status == OwnershipStatus.DISPUTED:
            raise ConflictError("This assignment is already disputed.")
        before = _ownership_snapshot(ownership)
        ownership.status = OwnershipStatus.DISPUTED.value
        ownership.decided_at = datetime.now().astimezone()
        ownership.reason = reason.strip()
        self._audit.record(
            actor=principal.actor,
            action=f"asset.{role}_disputed",
            subject_type="asset",
            subject_id=asset.id,
            reason=reason,
            before=before,
            after=_ownership_snapshot(ownership),
            reason_required=True,
        )
        self._repository.flush_asset_part(ownership)
        return self.get_asset(principal, asset.id)

    def _own_assignment(
        self, principal: Principal, asset: Asset, role: OwnershipRole
    ) -> AssetOwnership:
        """The assignment the caller holds; only the person it is assigned to may answer it."""
        ownership = next((o for o in asset.ownerships if o.role == role), None)
        if ownership is None:
            raise NotFoundError(
                f"This asset has no {role.value} assigned.", details={"role": role.value}
            )
        if ownership.user_id != principal.user_id or not principal.in_scope(asset.domain_id):
            raise PermissionDeniedError(
                "Only the person it is assigned to can answer this assignment.",
                details={"action": f"confirm_{role}"},
            )
        return ownership

    # --- Inbox

    def ownership_confirmations_due(self, principal: Principal) -> list[OwnershipDue]:
        """Assignments waiting for the caller to confirm or dispute, oldest first."""
        rows = self._repository.pending_ownerships(principal.user_id, principal.domain_ids)
        names = self._identity.get_users({o.assigned_by_id for o in rows})
        return [
            OwnershipDue(
                ownership_id=o.id,
                asset_id=o.asset_id,
                asset_name=o.asset.name,
                role=OwnershipRole(o.role),
                assigned_by=names[o.assigned_by_id].display_name
                if o.assigned_by_id in names
                else None,
                assigned_at=o.assigned_at,
                due_at=o.assigned_at + CONFIRMATION_PERIOD,
            )
            for o in rows
        ]
