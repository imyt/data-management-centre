"""Jobs and outbox: the platform schema with the job queue, outbox, heartbeats and idempotency keys.

Revision ID: c0db3a76993a
Revises: 7df075a1fb33
Created: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c0db3a76993a"
down_revision: str | Sequence[str] | None = "7df075a1fb33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA platform")
    op.create_table(
        "idempotency_key",
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column(
            "response_headers",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner", "key", name=op.f("pk_idempotency_key")),
        schema="platform",
    )
    op.create_index(
        "ix_idempotency_key_expires_at",
        "idempotency_key",
        ["expires_at"],
        unique=False,
        schema="platform",
    )
    op.create_table(
        "job",
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress", sa.SmallInteger(), nullable=True),
        sa.Column(
            "result", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_job_status"),
        ),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_job_progress")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
        sa.UniqueConstraint("kind", "idempotency_key", name=op.f("uq_job_kind_idempotency_key")),
        schema="platform",
    )
    op.create_index(
        "ix_job_queued",
        "job",
        ["run_after"],
        unique=False,
        schema="platform",
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "ix_job_running",
        "job",
        ["locked_at"],
        unique=False,
        schema="platform",
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_table(
        "outbox_event",
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_event")),
        schema="platform",
    )
    op.create_index(
        "ix_outbox_event_pending",
        "outbox_event",
        ["available_at"],
        unique=False,
        schema="platform",
        postgresql_where=sa.text("processed_at IS NULL"),
    )
    op.create_table(
        "worker_heartbeat",
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "beat_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("worker_id", name=op.f("pk_worker_heartbeat")),
        schema="platform",
    )
    op.create_table(
        "outbox_delivery",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("handler", sa.Text(), nullable=False),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["platform.outbox_event.id"],
            name=op.f("fk_outbox_delivery_event_id_outbox_event"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "handler", name=op.f("pk_outbox_delivery")),
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("outbox_delivery", schema="platform")
    op.drop_table("worker_heartbeat", schema="platform")
    op.drop_index(
        "ix_outbox_event_pending",
        table_name="outbox_event",
        schema="platform",
        postgresql_where=sa.text("processed_at IS NULL"),
    )
    op.drop_table("outbox_event", schema="platform")
    op.drop_index(
        "ix_job_running",
        table_name="job",
        schema="platform",
        postgresql_where=sa.text("status = 'running'"),
    )
    op.drop_index(
        "ix_job_queued",
        table_name="job",
        schema="platform",
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.drop_table("job", schema="platform")
    op.drop_index("ix_idempotency_key_expires_at", table_name="idempotency_key", schema="platform")
    op.drop_table("idempotency_key", schema="platform")
    op.execute("DROP SCHEMA platform")
