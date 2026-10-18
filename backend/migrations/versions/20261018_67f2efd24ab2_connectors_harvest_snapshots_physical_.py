"""Connectors: harvest snapshots, physical objects and mappings

Revision ID: 67f2efd24ab2
Revises: 2284b3698d16
Created: 2026-10-18 20:59:06.145346
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "67f2efd24ab2"
down_revision: str | Sequence[str] | None = "2284b3698d16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.execute("CREATE SCHEMA connectors")
    op.create_table(
        "harvest_snapshot",
        sa.Column("data_store_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "taken_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')", name=op.f("ck_harvest_snapshot_status")
        ),
        sa.CheckConstraint(
            "status <> 'failed' OR error IS NOT NULL",
            name=op.f("ck_harvest_snapshot_failure_has_error"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_harvest_snapshot")),
        schema="connectors",
    )
    op.create_index(
        op.f("ix_connectors_harvest_snapshot_data_store_id"),
        "harvest_snapshot",
        ["data_store_id"],
        unique=False,
        schema="connectors",
    )
    op.create_table(
        "physical_object",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("parent_path", sa.Text(), nullable=True),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("data_type", sa.Text(), nullable=True),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('schema', 'table', 'column')", name=op.f("ck_physical_object_kind")
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["connectors.harvest_snapshot.id"],
            name=op.f("fk_physical_object_snapshot_id_harvest_snapshot"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_physical_object")),
        sa.UniqueConstraint(
            "snapshot_id", "path", name=op.f("uq_physical_object_snapshot_id_path")
        ),
        schema="connectors",
    )
    op.create_table(
        "physical_object_mapping",
        sa.Column("data_store_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("data_element_id", sa.Uuid(), nullable=True),
        sa.Column("mapped_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "(asset_id IS NOT NULL) <> (data_element_id IS NOT NULL)",
            name=op.f("ck_physical_object_mapping_asset_or_element"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_physical_object_mapping")),
        sa.UniqueConstraint(
            "data_store_id", "path", name=op.f("uq_physical_object_mapping_data_store_id_path")
        ),
        schema="connectors",
    )


def downgrade() -> None:
    op.drop_table("physical_object_mapping", schema="connectors")
    op.drop_table("physical_object", schema="connectors")
    op.drop_index(
        op.f("ix_connectors_harvest_snapshot_data_store_id"),
        table_name="harvest_snapshot",
        schema="connectors",
    )
    op.drop_table("harvest_snapshot", schema="connectors")
    op.execute("DROP SCHEMA connectors")
