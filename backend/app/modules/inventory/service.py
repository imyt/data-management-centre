"""Public interface of the inventory module: the only file other modules import.

Every write checks the caller's role and domain scope, then records an audit event in the same
session, so the change and its event commit together (ADR 0006).
"""

import uuid
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
from app.modules.inventory.domain import LifecycleStatus
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
from app.modules.inventory.repository import InventoryRepository, ReferenceModel
from app.modules.inventory.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
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
