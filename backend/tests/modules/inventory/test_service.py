import uuid

import pytest
from sqlalchemy import Connection, select, text

from app.core.auth import Principal, Role
from app.core.db import Database
from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.inventory.domain import (
    Criticality,
    DataStoreType,
    EnvironmentType,
    Hosting,
    LifecycleStatus,
)
from app.modules.inventory.models import Domain, Region
from app.modules.inventory.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    DataStoreCreate,
    EnvironmentCreate,
)
from app.modules.inventory.service import (
    InventoryService,
    application_actions,
    application_list_actions,
)

CALLER = Principal(uuid.uuid4(), "Ana Owner", frozenset({Role.APPLICATION_OWNER}), None)
AUDITOR = Principal(uuid.uuid4(), "Aud Itor", frozenset({Role.AUDITOR}), None)


def _reference_id(database: Database, model: type[Domain] | type[Region], code: str) -> uuid.UUID:
    with database.transaction() as session:
        return session.scalars(select(model.id).where(model.code == code)).one()


def _new_app(domain_id: uuid.UUID, **overrides: object) -> ApplicationCreate:
    fields: dict[str, object] = {
        "name": "Order management",
        "code": "ORD",
        "domain_id": domain_id,
        "criticality": Criticality.HIGH,
        "hosting": Hosting.PUBLIC_CLOUD,
    }
    return ApplicationCreate.model_validate({**fields, **overrides})


def _audit_events(connection: Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        text("SELECT actor, action, subject_id, before, after FROM audit.audit_event ORDER BY seq")
    )
    return [dict(row._mapping) for row in rows]


@pytest.fixture
def finance(database: Database) -> uuid.UUID:
    return _reference_id(database, Domain, "finance")


@pytest.fixture
def eu(database: Database) -> uuid.UUID:
    return _reference_id(database, Region, "eu")


def test_reference_data_is_seeded(database: Database) -> None:
    with database.transaction() as session:
        service = InventoryService(session)
        for kind in ("domain", "data_category", "region", "retention_policy", "purpose"):
            assert len(service.list_reference(kind)) >= 4, kind


def test_create_application_records_an_audit_event(
    database: Database, db_connection: Connection, finance: uuid.UUID
) -> None:
    with database.transaction() as session:
        application = InventoryService(session).create_application(CALLER, _new_app(finance))

    assert application.lifecycle_status == "planned"
    assert application.domain.code == "finance"
    [event] = _audit_events(db_connection)
    assert event["actor"] == CALLER.actor
    assert event["action"] == "application.created"
    assert event["subject_id"] == str(application.id)
    assert event["after"]["code"] == "ORD"  # type: ignore[index]


def test_codes_are_unique_ignoring_case(database: Database, finance: uuid.UUID) -> None:
    with database.transaction() as session:
        InventoryService(session).create_application(CALLER, _new_app(finance))

    with pytest.raises(ConflictError), database.transaction() as session:
        InventoryService(session).create_application(CALLER, _new_app(finance, code="ord"))


def test_unknown_domain_is_invalid_input(database: Database) -> None:
    with pytest.raises(InvalidInputError, match="domain"), database.transaction() as session:
        InventoryService(session).create_application(CALLER, _new_app(uuid.uuid4()))


def test_update_records_only_the_changed_fields(
    database: Database, db_connection: Connection, finance: uuid.UUID
) -> None:
    with database.transaction() as session:
        service = InventoryService(session)
        created = service.create_application(CALLER, _new_app(finance))
        updated = service.update_application(
            CALLER,
            created.id,
            ApplicationUpdate(name="Orders", lifecycle_status=LifecycleStatus.ACTIVE),
        )

    assert updated.name == "Orders"
    event = _audit_events(db_connection)[-1]
    assert event["action"] == "application.updated"
    assert event["before"] == {"lifecycle_status": "planned", "name": "Order management"}
    assert event["after"] == {"lifecycle_status": "active", "name": "Orders"}


def test_update_without_changes_records_nothing(
    database: Database, db_connection: Connection, finance: uuid.UUID
) -> None:
    with database.transaction() as session:
        service = InventoryService(session)
        created = service.create_application(CALLER, _new_app(finance))
        service.update_application(CALLER, created.id, ApplicationUpdate(name="Order management"))

    assert [e["action"] for e in _audit_events(db_connection)] == ["application.created"]


def test_lifecycle_moves_only_forward_one_step(database: Database, finance: uuid.UUID) -> None:
    with database.transaction() as session:
        created = InventoryService(session).create_application(CALLER, _new_app(finance))

    for target in (LifecycleStatus.RETIRING, LifecycleStatus.DECOMMISSIONED):
        with pytest.raises(InvalidInputError, match="cannot move"), database.transaction() as s:
            InventoryService(s).update_application(
                CALLER, created.id, ApplicationUpdate(lifecycle_status=target)
            )


def test_environments_and_data_stores_belong_to_the_application(
    database: Database, db_connection: Connection, finance: uuid.UUID, eu: uuid.UUID
) -> None:
    with database.transaction() as session:
        service = InventoryService(session)
        application = service.create_application(CALLER, _new_app(finance))
        environment = service.add_environment(
            CALLER,
            application.id,
            EnvironmentCreate(name="Production", type=EnvironmentType.PRODUCTION, region_id=eu),
        )
        store = service.add_data_store(
            CALLER,
            environment.id,
            DataStoreCreate(
                name="orders-db",
                type=DataStoreType.RELATIONAL,
                platform="PostgreSQL 18",
                region_id=eu,
                connection_ref="vault:dmc/orders-db",
            ),
        )
        detail = service.get_application(application.id)

    assert store.harvest_status == "never"
    assert [e.name for e in detail.environments] == ["Production"]
    assert [s.name for s in detail.environments[0].data_stores] == ["orders-db"]
    actions = [(e["action"], e["subject_id"]) for e in _audit_events(db_connection)]
    assert actions == [
        ("application.created", str(application.id)),
        ("app_environment.created", str(application.id)),
        ("data_store.created", str(application.id)),
    ]


def test_missing_environment_is_not_found(database: Database, eu: uuid.UUID) -> None:
    body = DataStoreCreate(
        name="x",
        type=DataStoreType.RELATIONAL,
        platform="PostgreSQL",
        region_id=eu,
        connection_ref="vault:x",
    )
    with pytest.raises(NotFoundError), database.transaction() as session:
        InventoryService(session).add_data_store(CALLER, uuid.uuid4(), body)


def test_list_filters_searches_and_pages(database: Database, finance: uuid.UUID) -> None:
    customer = _reference_id(database, Domain, "customer")
    with database.transaction() as session:
        service = InventoryService(session)
        for code, name, domain in [
            ("BIL", "Billing", finance),
            ("CRM", "Customer portal", customer),
            ("GL", "General ledger", finance),
            ("PAY", "Payroll", finance),
        ]:
            service.create_application(
                CALLER,
                _new_app(domain, code=code, name=name, lifecycle_status=LifecycleStatus.ACTIVE),
            )
        first = service.list_applications(limit=2, cursor=None, domain_id=finance)
        second = service.list_applications(limit=2, cursor=first.next_cursor, domain_id=finance)
        searched = service.list_applications(limit=10, cursor=None, query="LEDG")
        planned = service.list_applications(
            limit=10, cursor=None, lifecycle_status=LifecycleStatus.PLANNED
        )

    assert [a.code for a in first.items] == ["BIL", "GL"]
    assert first.total == 3
    assert [a.code for a in second.items] == ["PAY"]
    assert second.next_cursor is None
    assert [a.code for a in searched.items] == ["GL"]
    assert planned.items == []


def test_roles_and_domain_scope_decide_writes_and_allowed_actions(
    database: Database, finance: uuid.UUID
) -> None:
    customer = _reference_id(database, Domain, "customer")
    customer_owner = Principal(
        uuid.uuid4(), "Cy Owner", frozenset({Role.APPLICATION_OWNER}), frozenset({customer})
    )
    with database.transaction() as session:
        application = InventoryService(session).create_application(CALLER, _new_app(finance))

    assert application_list_actions(AUDITOR) == []
    assert application_actions(AUDITOR, application) == []
    assert application_actions(customer_owner, application) == []
    assert application_actions(CALLER, application) == ["add_data_store", "add_environment", "edit"]
    with pytest.raises(PermissionDeniedError), database.transaction() as session:
        InventoryService(session).create_application(AUDITOR, _new_app(finance, code="X1"))
    with pytest.raises(PermissionDeniedError), database.transaction() as session:
        InventoryService(session).update_application(
            customer_owner, application.id, ApplicationUpdate(name="Mine now")
        )
