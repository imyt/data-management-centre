"""`dmc-seed`: loads the local data set through the module services (ADR 0004 §8).

    uv run dmc-seed

Creates the dev personas (without them every request is "not signed in"), a sample application
whose data store is the local `estate` database, and the estate's sample tables. The reference
data (domains, regions, retention policies, …) comes with the migrations. Writes to
DMC_DATABASE_URL and refuses to run in staging or production. Safe to run again.
"""

import sys
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.config import PROTECTED, get_settings
from app.core.db import Database, create_database_engine
from app.estate import EstateLoad, load_estate
from app.modules.identity.personas import CUSTOMER
from app.modules.identity.service import IdentityDirectory, IdentityService
from app.modules.inventory.domain import Criticality, DataStoreType, Hosting, LifecycleStatus
from app.modules.inventory.schemas import ApplicationCreate, DataStoreCreate, EnvironmentCreate
from app.modules.inventory.service import InventoryService
from app.modules.policy.schemas import ControlCreate, PolicyCreate, SelectorBody
from app.modules.policy.service import PolicyService

SAMPLE_CODE = "SHOP"
# Harvest resolves this reference to the read-only dmc_harvest URL (backend/.env.example).
ESTATE_CONNECTION_REF = "env:DMC_ESTATE_HARVEST_URL"
_SEEDER = "hannah.becker"  # Governance: may register applications in every domain


def seed_sample_application(session: Session) -> bool:
    """Register the sample application with its `estate` data store. False if already there."""
    inventory = InventoryService(session)
    principal = IdentityDirectory().principal_for(session, _SEEDER)
    if principal is None:
        raise RuntimeError(f"The persona {_SEEDER} is missing; seed the personas first.")
    existing = inventory.list_applications(principal, limit=1, cursor=None, query=SAMPLE_CODE)
    if any(a.code == SAMPLE_CODE for a in existing.items):
        return False

    users = IdentityService(session)
    owner, tech = users.find_by_username("marcus.webb"), users.find_by_username("priya.raman")
    region = next(r for r in inventory.list_reference("region") if r.code == "eu")
    application = inventory.create_application(
        principal,
        ApplicationCreate(
            name="Online Shop",
            code=SAMPLE_CODE,
            description="Sample web shop. Its tables are the local `estate` database.",
            domain_id=CUSTOMER,
            criticality=Criticality.HIGH,
            hosting=Hosting.PRIVATE_CLOUD,
            lifecycle_status=LifecycleStatus.ACTIVE,
            app_owner_id=owner.id if owner else None,
            tech_owner_id=tech.id if tech else None,
        ),
    )
    environment = inventory.add_environment(
        principal,
        application.id,
        EnvironmentCreate(name="Production", type="production", region_id=region.id),
    )
    inventory.add_data_store(
        principal,
        environment.id,
        DataStoreCreate(
            name="estate",
            type=DataStoreType.RELATIONAL,
            platform="PostgreSQL 18",
            region_id=region.id,
            connection_ref=ESTATE_CONNECTION_REF,
        ),
    )
    return True


# The starter control library: one policy per concern, each with a control the evaluation engine
# can run once it lands. Selectors name attributes only.
_POLICIES = (
    PolicyCreate(
        code="RET",
        name="Data retention",
        statement="Personal and business data is kept no longer than its retention policy allows.",
    ),
    PolicyCreate(
        code="KNOW",
        name="Know our data",
        statement="Every stored dataset and every system holding data has a named, current owner.",
    ),
)
# (policy code, control) pairs.
_CONTROLS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "RET",
        {
            "code": "RET-01",
            "name": "Stored data is deleted at the end of its retention period",
            "description": "The oldest record of a stored asset is within the retention policy "
            "declared for it.",
            "rule_type": "retention_window",
            "evidence_requirement": "A harvest showing the oldest record, or a deletion log.",
            "params": {"grace_days": 0},
            "selector": SelectorBody(subject="asset", where={"is_stored": True}),
        },
    ),
    (
        "KNOW",
        {
            "code": "KNOW-01",
            "name": "Production data stores are harvested regularly",
            "description": "Every production data store has been harvested successfully "
            "recently, so what we know about it is current.",
            "rule_type": "harvest_fresh",
            "evidence_requirement": "The harvest history of the data store.",
            "params": {"max_age_hours": 48},
            "selector": SelectorBody(
                subject="data_store", where={"environment_type": "production"}
            ),
        },
    ),
    (
        "KNOW",
        {
            "code": "KNOW-02",
            "name": "Personal data assets are fully declared",
            "description": "Assets with personal data have a category, a business context and "
            "an owner.",
            "rule_type": "declaration_complete",
            "evidence_requirement": "The asset's declarations in the inventory.",
            "params": {"required_fields": ["business_context", "data_category", "owner"]},
            "selector": SelectorBody(subject="asset", where={"contains_pii": True}),
        },
    ),
)


def seed_policies(session: Session) -> int:
    """Add the starter policies and controls that are missing. Returns how many controls it added,
    then derives their applied controls so the Controls area is populated without a worker."""
    service = PolicyService(session)
    principal = IdentityDirectory().principal_for(session, _SEEDER)
    if principal is None:
        raise RuntimeError(f"The persona {_SEEDER} is missing; seed the personas first.")
    policies = {p.code: p for p in service.list_policies()}
    for data in _POLICIES:
        if data.code not in policies:
            policies[data.code] = service.create_policy(
                principal, data.model_copy(update={"owner_id": principal.user_id})
            )
    existing = {c.code for c in service.list_controls(limit=100, cursor=None).items}
    added = 0
    for policy_code, fields in _CONTROLS:
        if fields["code"] in existing:
            continue
        service.create_control(
            principal,
            ControlCreate(
                policy_id=policies[policy_code].id, control_owner_id=principal.user_id, **fields
            ),
        )
        added += 1
    service.recompute_all()
    return added


def seed_estate(engine: Engine) -> EstateLoad:
    with engine.begin() as connection:
        return load_estate(connection)


def main() -> int:
    settings = get_settings()
    if settings.environment in PROTECTED:
        print(
            f"dmc-seed refuses to run in the {settings.environment} environment.", file=sys.stderr
        )
        return 2
    if not settings.database_url:
        print("Set DMC_DATABASE_URL (see backend/.env.example).", file=sys.stderr)
        return 2
    engine = create_database_engine(settings.database_url)
    try:
        with Database(engine).transaction() as session:
            personas = IdentityService(session).seed_personas()
            session.flush()
            registered = seed_sample_application(session)
            controls = seed_policies(session)
    finally:
        engine.dispose()
    print(f"Seeded {len(personas)} new personas.")
    print("Registered the sample application." if registered else "Sample application present.")
    print(f"Added {controls} starter controls." if controls else "Starter controls present.")

    if not settings.estate_migration_url:
        print("DMC_ESTATE_MIGRATION_URL is not set; skipped the estate sample tables.")
        return 0
    estate_engine = create_database_engine(settings.estate_migration_url)
    try:
        load = seed_estate(estate_engine)
    finally:
        estate_engine.dispose()
    print(f"Estate: {load.tables_created} tables created, {load.rows_inserted} rows inserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
