"""Policy: policies, controls, rule versions and applied controls

Revision ID: 575bb450f9b8
Revises: 67f2efd24ab2
Created: 2026-10-18 21:16:23.860878
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "575bb450f9b8"
down_revision: str | Sequence[str] | None = "67f2efd24ab2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA policy")
    op.create_table(
        "policy",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy")),
        sa.UniqueConstraint("code", name=op.f("uq_policy_code")),
        schema="policy",
    )
    op.create_table(
        "control",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("control_owner_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_requirement", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("retired_reason", sa.Text(), nullable=True),
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
            "status <> 'retired' OR retired_reason IS NOT NULL",
            name=op.f("ck_control_retired_reason"),
        ),
        sa.CheckConstraint("status IN ('active', 'retired')", name=op.f("ck_control_status")),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["policy.policy.id"], name=op.f("fk_control_policy_id_policy")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_control")),
        sa.UniqueConstraint("code", name=op.f("uq_control_code")),
        schema="policy",
    )
    op.create_index(
        op.f("ix_policy_control_policy_id"), "control", ["policy_id"], unique=False, schema="policy"
    )
    op.create_index(
        op.f("ix_policy_control_rule_type"), "control", ["rule_type"], unique=False, schema="policy"
    )
    op.create_table(
        "rule_version",
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selector", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.CheckConstraint("version > 0", name=op.f("ck_rule_version_version_positive")),
        sa.ForeignKeyConstraint(
            ["control_id"], ["policy.control.id"], name=op.f("fk_rule_version_control_id_control")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_version")),
        sa.UniqueConstraint(
            "control_id", "version", name=op.f("uq_rule_version_control_id_version")
        ),
        schema="policy",
    )
    op.create_index(
        op.f("ix_policy_rule_version_control_id"),
        "rule_version",
        ["control_id"],
        unique=False,
        schema="policy",
    )
    op.create_table(
        "applied_control",
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("subject_name", sa.Text(), nullable=False),
        sa.Column("subject_domain_id", sa.Uuid(), nullable=False),
        sa.Column("accountable_id", sa.Uuid(), nullable=True),
        sa.Column("responsible_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("derived_from", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "derived_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_reason", sa.Text(), nullable=True),
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
            "status <> 'retired' OR (retired_at IS NOT NULL AND retired_reason IS NOT NULL)",
            name=op.f("ck_applied_control_retired_has_reason"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'retired')", name=op.f("ck_applied_control_status")
        ),
        sa.CheckConstraint(
            "subject_type IN ('asset', 'data_store', 'application')",
            name=op.f("ck_applied_control_subject_type"),
        ),
        sa.ForeignKeyConstraint(
            ["control_id"],
            ["policy.control.id"],
            name=op.f("fk_applied_control_control_id_control"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_version_id"],
            ["policy.rule_version.id"],
            name=op.f("fk_applied_control_rule_version_id_rule_version"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applied_control")),
        schema="policy",
    )
    op.create_index(
        "ix_applied_control_subject",
        "applied_control",
        ["subject_type", "subject_id"],
        unique=False,
        schema="policy",
    )
    op.create_index(
        op.f("ix_policy_applied_control_control_id"),
        "applied_control",
        ["control_id"],
        unique=False,
        schema="policy",
    )
    op.create_index(
        op.f("ix_policy_applied_control_subject_domain_id"),
        "applied_control",
        ["subject_domain_id"],
        unique=False,
        schema="policy",
    )
    op.create_index(
        "uq_applied_control_active",
        "applied_control",
        ["control_id", "subject_type", "subject_id"],
        unique=True,
        schema="policy",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.execute(
        """
        CREATE FUNCTION policy.reject_rule_version_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'policy.rule_version is immutable: publish a new version instead';
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER rule_version_immutable BEFORE UPDATE OR DELETE ON policy.rule_version
        FOR EACH ROW EXECUTE FUNCTION policy.reject_rule_version_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER rule_version_immutable ON policy.rule_version")
    op.execute("DROP FUNCTION policy.reject_rule_version_change()")
    op.drop_index(
        "uq_applied_control_active",
        table_name="applied_control",
        schema="policy",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_index(
        op.f("ix_policy_applied_control_subject_domain_id"),
        table_name="applied_control",
        schema="policy",
    )
    op.drop_index(
        op.f("ix_policy_applied_control_control_id"), table_name="applied_control", schema="policy"
    )
    op.drop_index("ix_applied_control_subject", table_name="applied_control", schema="policy")
    op.drop_table("applied_control", schema="policy")
    op.drop_index(
        op.f("ix_policy_rule_version_control_id"), table_name="rule_version", schema="policy"
    )
    op.drop_table("rule_version", schema="policy")
    op.drop_index(op.f("ix_policy_control_rule_type"), table_name="control", schema="policy")
    op.drop_index(op.f("ix_policy_control_policy_id"), table_name="control", schema="policy")
    op.drop_table("control", schema="policy")
    op.drop_table("policy", schema="policy")
    op.execute("DROP SCHEMA policy")
