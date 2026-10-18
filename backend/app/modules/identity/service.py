"""Public interface of the identity module: the only file other modules and app.main import."""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.auth import Principal, Role
from app.core.errors import ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.identity.models import DomainScope, RoleAssignment, UserAccount
from app.modules.identity.personas import DEFAULT_PERSONA, PERSONAS
from app.modules.identity.repository import UserRepository

SEED_ACTOR = "system:seed"


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    roles: frozenset[Role]
    domain_ids: frozenset[uuid.UUID] | None  # None: every domain

    def principal(self) -> Principal:
        return Principal(self.id, self.display_name, self.roles, self.domain_ids)


@dataclass(frozen=True)
class NewUser:
    username: str
    display_name: str
    roles: frozenset[Role]
    domain_ids: frozenset[uuid.UUID] | None
    email: str | None = None


def _to_user(row: UserAccount) -> User:
    return User(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        email=row.email,
        roles=frozenset(Role(r.role) for r in row.roles),
        domain_ids=None if row.all_domains else frozenset(s.domain_id for s in row.domain_scopes),
    )


def _audit_view(user: User) -> dict[str, object]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "roles": sorted(user.roles),
        "domain_ids": None if user.domain_ids is None else sorted(map(str, user.domain_ids)),
    }


class IdentityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)

    def get_user(self, user_id: uuid.UUID) -> User:
        row = self._users.get(user_id)
        if row is None:
            raise NotFoundError("There is no such user.", details={"user_id": str(user_id)})
        return _to_user(row)

    def find_by_username(self, username: str) -> User | None:
        """The active user with this username, or None."""
        row = self._users.by_username(username)
        return _to_user(row) if row is not None and row.active else None

    def get_users(self, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
        """The users with these ids (active or not), by id; unknown ids are left out."""
        return {row.id: _to_user(row) for row in self._users.by_ids(user_ids)}

    def list_active_users(self) -> list[User]:
        return [_to_user(row) for row in self._users.active()]

    def create_user(self, new: NewUser, *, actor: str) -> User:
        if self._users.by_username(new.username) is not None:
            raise ConflictError(
                f"A user called {new.username!r} already exists.", details={"field": "username"}
            )
        row = self._users.add(
            UserAccount(
                username=new.username,
                display_name=new.display_name,
                email=new.email,
                all_domains=new.domain_ids is None,
                roles=[RoleAssignment(role=role.value) for role in sorted(new.roles)],
                domain_scopes=[DomainScope(domain_id=d) for d in sorted(new.domain_ids or ())],
            )
        )
        user = _to_user(row)
        AuditService(self._session).record(
            actor=actor,
            action="identity.user_created",
            subject_type="user",
            subject_id=user.id,
            after=_audit_view(user),
        )
        return user

    def seed_personas(self) -> list[User]:
        """Create the dev personas that don't exist yet. Safe to run again."""
        return [
            self.create_user(
                NewUser(
                    username=p.username,
                    display_name=p.display_name,
                    roles=frozenset({p.role}),
                    domain_ids=p.domain_ids,
                ),
                actor=SEED_ACTOR,
            )
            for p in PERSONAS
            if self._users.by_username(p.username) is None
        ]


class IdentityDirectory:
    """The `UserDirectory` core authentication resolves users through (wired in app.main)."""

    default_dev_username = DEFAULT_PERSONA

    def principal_for(self, session: Session, username: str) -> Principal | None:
        user = IdentityService(session).find_by_username(username)
        return user.principal() if user is not None else None
