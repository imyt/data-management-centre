"""Baseline: an empty starting point, so every database carries a revision from day one.

Revision ID: 8dc8fe034a03
Revises:
Created: 2026-10-18
"""

from collections.abc import Sequence

revision: str = "8dc8fe034a03"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
