"""`dmc-seed`: loads the local data set through the module services (ADR 0004 §8).

    uv run dmc-seed

Creates the dev personas (without them every request is "not signed in"), a sample application
whose data store is the local `estate` database, and the estate's sample tables. The reference
data (domains, regions, retention policies, …) comes with the migrations. Writes to
DMC_DATABASE_URL and refuses to run in staging or production. Safe to run again.
"""

import sys

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
    finally:
        engine.dispose()
    print(f"Seeded {len(personas)} new personas.")
    print("Registered the sample application." if registered else "Sample application present.")

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
