"""Inventory: the inventory schema, seeded reference data, applications, environments, data stores.

Revision ID: 815751cc92eb
Revises: c0db3a76993a
Created: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "815751cc92eb"
down_revision: str | Sequence[str] | None = "c0db3a76993a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA inventory")
    op.create_table(
        "data_category",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_category")),
        sa.UniqueConstraint("code", name=op.f("uq_data_category_code")),
        schema="inventory",
    )
    op.create_table(
        "domain",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domain")),
        sa.UniqueConstraint("code", name=op.f("uq_domain_code")),
        schema="inventory",
    )
    op.create_table(
        "purpose",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purpose")),
        sa.UniqueConstraint("code", name=op.f("uq_purpose_code")),
        schema="inventory",
    )
    op.create_table(
        "region",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_region")),
        sa.UniqueConstraint("code", name=op.f("uq_region_code")),
        schema="inventory",
    )
    op.create_table(
        "retention_policy",
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "retention_days > 0", name=op.f("ck_retention_policy_retention_days_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_policy")),
        sa.UniqueConstraint("code", name=op.f("uq_retention_policy_code")),
        schema="inventory",
    )
    op.create_table(
        "application",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("app_owner_id", sa.Uuid(), nullable=True),
        sa.Column("tech_owner_id", sa.Uuid(), nullable=True),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column("criticality", sa.Text(), nullable=False),
        sa.Column("hosting", sa.Text(), nullable=False),
        sa.Column("lifecycle_status", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "criticality IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_application_criticality"),
        ),
        sa.CheckConstraint(
            "hosting IN ('on_premises', 'private_cloud', 'public_cloud', 'saas')",
            name=op.f("ck_application_hosting"),
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('planned', 'active', 'retiring', 'decommissioned')",
            name=op.f("ck_application_lifecycle_status"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"], ["inventory.domain.id"], name=op.f("fk_application_domain_id_domain")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application")),
        sa.UniqueConstraint("code", name=op.f("uq_application_code")),
        schema="inventory",
    )
    op.create_index(
        op.f("ix_inventory_application_domain_id"),
        "application",
        ["domain_id"],
        unique=False,
        schema="inventory",
    )
    op.create_index(
        op.f("ix_inventory_application_lifecycle_status"),
        "application",
        ["lifecycle_status"],
        unique=False,
        schema="inventory",
    )
    op.create_index(
        op.f("ix_inventory_application_name"),
        "application",
        ["name"],
        unique=False,
        schema="inventory",
    )
    op.create_table(
        "app_environment",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("region_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('production', 'non_production')", name=op.f("ck_app_environment_type")
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["inventory.application.id"],
            name=op.f("fk_app_environment_application_id_application"),
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["inventory.region.id"], name=op.f("fk_app_environment_region_id_region")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_environment")),
        schema="inventory",
    )
    op.create_index(
        op.f("ix_inventory_app_environment_application_id"),
        "app_environment",
        ["application_id"],
        unique=False,
        schema="inventory",
    )
    op.create_table(
        "data_store",
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("region_id", sa.Uuid(), nullable=False),
        sa.Column("connection_ref", sa.Text(), nullable=False),
        sa.Column("harvest_status", sa.Text(), server_default="never", nullable=False),
        sa.Column("last_harvested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "harvest_status IN ('never', 'succeeded', 'failed')",
            name=op.f("ck_data_store_harvest_status"),
        ),
        sa.CheckConstraint(
            "type IN ('relational', 'document', 'object_storage', 'warehouse', 'file_share')",
            name=op.f("ck_data_store_type"),
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["inventory.app_environment.id"],
            name=op.f("fk_data_store_environment_id_app_environment"),
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["inventory.region.id"], name=op.f("fk_data_store_region_id_region")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_store")),
        schema="inventory",
    )
    op.create_index(
        op.f("ix_inventory_data_store_environment_id"),
        "data_store",
        ["environment_id"],
        unique=False,
        schema="inventory",
    )
    _seed_reference_data()


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_data_store_environment_id"), table_name="data_store", schema="inventory"
    )
    op.drop_table("data_store", schema="inventory")
    op.drop_index(
        op.f("ix_inventory_app_environment_application_id"),
        table_name="app_environment",
        schema="inventory",
    )
    op.drop_table("app_environment", schema="inventory")
    op.drop_index(
        op.f("ix_inventory_application_name"), table_name="application", schema="inventory"
    )
    op.drop_index(
        op.f("ix_inventory_application_lifecycle_status"),
        table_name="application",
        schema="inventory",
    )
    op.drop_index(
        op.f("ix_inventory_application_domain_id"), table_name="application", schema="inventory"
    )
    op.drop_table("application", schema="inventory")
    op.drop_table("retention_policy", schema="inventory")
    op.drop_table("region", schema="inventory")
    op.drop_table("purpose", schema="inventory")
    op.drop_table("domain", schema="inventory")
    op.drop_table("data_category", schema="inventory")
    op.execute("DROP SCHEMA inventory")


# Starting reference data (FR-D2), so forms have something to choose from. Edited in DMC later.
_REFERENCE_DATA: dict[str, list[dict[str, object]]] = {
    # Fixed ids: identity's dev personas are scoped to these (app/modules/identity/personas.py).
    "domain": [
        {
            "id": "0199f000-0000-7000-8000-000000000001",
            "code": "customer",
            "name": "Customer",
            "description": "Customer profiles and contact.",
        },
        {
            "id": "0199f000-0000-7000-8000-000000000002",
            "code": "finance",
            "name": "Finance",
            "description": "Ledgers, payments and reporting.",
        },
        {
            "id": "0199f000-0000-7000-8000-000000000003",
            "code": "people",
            "name": "People",
            "description": "Employees, payroll and recruiting.",
        },
        {
            "id": "0199f000-0000-7000-8000-000000000004",
            "code": "operations",
            "name": "Operations",
            "description": "Orders, fulfilment, supply.",
        },
        {
            "id": "0199f000-0000-7000-8000-000000000005",
            "code": "marketing",
            "name": "Marketing",
            "description": "Campaigns, consent, analytics.",
        },
    ],
    "data_category": [
        {"code": "personal", "name": "Personal", "description": "Identifies a living person."},
        {"code": "payment", "name": "Payment", "description": "Card and bank account data."},
        {"code": "financial", "name": "Financial", "description": "Ledgers and transactions."},
        {"code": "employee", "name": "Employee", "description": "Data about staff."},
        {"code": "operational", "name": "Operational", "description": "No personal data."},
    ],
    "region": [
        {"code": "eu", "name": "European Union", "description": None},
        {"code": "uk", "name": "United Kingdom", "description": None},
        {"code": "us", "name": "United States", "description": None},
        {"code": "apac", "name": "Asia Pacific", "description": None},
    ],
    "retention_policy": [
        {"code": "r30d", "name": "30 days", "description": "Transient data.", "retention_days": 30},
        {
            "code": "r1y",
            "name": "1 year",
            "description": "Operational logs.",
            "retention_days": 365,
        },
        {
            "code": "r7y",
            "name": "7 years",
            "description": "Financial records.",
            "retention_days": 2555,
        },
        {"code": "r10y", "name": "10 years", "description": "Contracts.", "retention_days": 3650},
    ],
    "purpose": [
        {"code": "service", "name": "Service delivery", "description": "Provide the service."},
        {"code": "billing", "name": "Billing", "description": "Invoice and collect payment."},
        {"code": "analytics", "name": "Analytics", "description": "Aggregate reporting."},
        {"code": "compliance", "name": "Legal compliance", "description": "Meet legal duties."},
        {"code": "marketing", "name": "Marketing", "description": "With consent only."},
    ],
}


def _seed_reference_data() -> None:
    for table_name, rows in _REFERENCE_DATA.items():
        columns = [sa.column("code"), sa.column("name"), sa.column("description")]
        if table_name == "domain":
            columns.append(sa.column("id", sa.Uuid()))
        if table_name == "retention_policy":
            columns.append(sa.column("retention_days"))
        op.bulk_insert(sa.table(table_name, *columns, schema="inventory"), rows)
