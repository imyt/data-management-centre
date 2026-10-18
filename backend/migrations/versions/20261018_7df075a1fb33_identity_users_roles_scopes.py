"""Identity: users, their role assignments and domain scopes (ADR 0007).

Personas are seeded by `dmc-seed`, not here, so deployed databases start without them.

Revision ID: 7df075a1fb33
Revises: 02f154d112c1
Created: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7df075a1fb33"
down_revision: str | Sequence[str] | None = "02f154d112c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA identity")
    op.create_table(
        "user_account",
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("all_domains", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_account")),
        sa.UniqueConstraint("username", name=op.f("uq_user_account_username")),
        schema="identity",
    )
    op.create_table(
        "domain_scope",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.user_account.id"],
            name=op.f("fk_domain_scope_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domain_scope")),
        sa.UniqueConstraint("user_id", "domain_id", name=op.f("uq_domain_scope_user_id_domain_id")),
        schema="identity",
    )
    op.create_table(
        "role_assignment",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('data_owner', 'application_owner', 'data_steward', 'process_owner', "
            "'governance', 'leadership', 'auditor')",
            name=op.f("ck_role_assignment_known_role"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.user_account.id"],
            name=op.f("fk_role_assignment_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_assignment")),
        sa.UniqueConstraint("user_id", "role", name=op.f("uq_role_assignment_user_id_role")),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_table("role_assignment", schema="identity")
    op.drop_table("domain_scope", schema="identity")
    op.drop_table("user_account", schema="identity")
    op.execute("DROP SCHEMA identity")
