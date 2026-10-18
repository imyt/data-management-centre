"""Audit event chain: the audit schema and its append-only, hash-chained audit_event table.

Revision ID: 02f154d112c1
Revises: 8dc8fe034a03
Created: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "02f154d112c1"
down_revision: str | Sequence[str] | None = "8dc8fe034a03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA audit")
    op.create_table(
        "audit_event",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
        sa.UniqueConstraint("hash", name=op.f("uq_audit_event_hash")),
        sa.UniqueConstraint("seq", name=op.f("uq_audit_event_seq")),
        schema="audit",
    )
    op.create_index(
        "ix_audit_event_subject",
        "audit_event",
        ["subject_type", "subject_id", "seq"],
        unique=False,
        schema="audit",
    )

    # Append-only (FR-U1): reject UPDATE, DELETE and TRUNCATE for every role, the owner included.
    op.execute("""
        CREATE FUNCTION audit.reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit.audit_event is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
    """)
    op.execute("""
        CREATE TRIGGER audit_event_append_only
        BEFORE UPDATE OR DELETE ON audit.audit_event
        FOR EACH ROW EXECUTE FUNCTION audit.reject_change()
    """)
    op.execute("""
        CREATE TRIGGER audit_event_no_truncate
        BEFORE TRUNCATE ON audit.audit_event
        FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_change()
    """)
    # The runtime role (ADR 0004 §2) gets DML by default privileges; take back all but INSERT.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'dmc_app') THEN
                REVOKE UPDATE, DELETE, TRUNCATE ON audit.audit_event FROM dmc_app;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.drop_table("audit_event", schema="audit")
    op.execute("DROP FUNCTION audit.reject_change()")
    op.execute("DROP SCHEMA audit")
