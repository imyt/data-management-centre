"""The `identity` schema. Domain ids are references to inventory domains: no cross-schema FKs."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.auth import Role
from app.core.db import Base, Timestamps, UUIDv7PrimaryKey

_ROLE_NAMES = ", ".join(f"'{role.value}'" for role in Role)


class UserAccount(UUIDv7PrimaryKey, Timestamps, Base):
    __tablename__ = "user_account"
    __table_args__ = ({"schema": "identity"},)

    # The name a user signs in with; in dev mode, the value of the X-DMC-Dev-User header.
    username: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(server_default=text("true"))
    # True: every domain, and domain_scopes is ignored.
    all_domains: Mapped[bool] = mapped_column(server_default=text("false"))

    roles: Mapped[list["RoleAssignment"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="RoleAssignment.role"
    )
    domain_scopes: Mapped[list["DomainScope"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class RoleAssignment(UUIDv7PrimaryKey, Base):
    __tablename__ = "role_assignment"
    __table_args__ = (
        UniqueConstraint("user_id", "role"),
        CheckConstraint(f"role IN ({_ROLE_NAMES})", name="known_role"),
        {"schema": "identity"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity.user_account.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DomainScope(UUIDv7PrimaryKey, Base):
    __tablename__ = "domain_scope"
    __table_args__ = (UniqueConstraint("user_id", "domain_id"), {"schema": "identity"})

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity.user_account.id", ondelete="CASCADE")
    )
    # inventory's domain id; a reference only (ARCHITECTURE §5: no module writes another's tables).
    domain_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
