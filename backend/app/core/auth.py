"""Who is calling: the principal, how requests are authenticated, and authorisation (ADR 0007).

Routes take a `PrincipalDep`. Services take the `Principal` and call `require(...)` before a change;
the API computes `allowed_actions` with `allowed_actions(...)` from the same `Permission`s.

Core never imports modules: users are resolved through the `UserDirectory` protocol, which the
identity module implements and `app.main` passes to `configure_authentication`.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Protocol

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import SessionDep
from app.core.errors import NotFoundError, PermissionDeniedError, UnauthenticatedError

AuthMode = Literal["dev", "oidc"]

DEV_USER_HEADER = "X-DMC-Dev-User"

# Environments where a request without a dev-user header acts as the default persona.
_DEFAULT_PERSONA_ENVIRONMENTS = frozenset({"local", "dev"})


class Role(StrEnum):
    """The roles in PRD.md §2."""

    DATA_OWNER = "data_owner"
    APPLICATION_OWNER = "application_owner"
    DATA_STEWARD = "data_steward"
    PROCESS_OWNER = "process_owner"
    GOVERNANCE = "governance"
    LEADERSHIP = "leadership"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller. Both auth modes produce the same shape.

    `domain_ids` is the set of domains the caller may act in; `None` means every domain.
    """

    user_id: uuid.UUID
    display_name: str
    roles: frozenset[Role]
    domain_ids: frozenset[uuid.UUID] | None

    @property
    def actor(self) -> str:
        """The audit trail's `actor` for this caller."""
        return f"user:{self.user_id}"

    def has_any_role(self, roles: Iterable[Role]) -> bool:
        return not self.roles.isdisjoint(roles)

    def in_scope(self, domain_id: uuid.UUID | None) -> bool:
        """Whether a subject in `domain_id` is in scope. `None`: the subject has no domain."""
        return self.domain_ids is None or domain_id is None or domain_id in self.domain_ids


class UserDirectory(Protocol):
    """Looks users up for authentication. Implemented by the identity module."""

    default_dev_username: str

    def principal_for(self, session: Session, username: str) -> Principal | None:
        """The principal for an active user, or None if there is no such user."""
        ...


@dataclass(frozen=True)
class Authentication:
    mode: AuthMode
    directory: UserDirectory
    # Username used when a dev-mode request names no user; None makes the header required.
    default_dev_username: str | None


def configure_authentication(app: FastAPI, settings: Settings, directory: UserDirectory) -> None:
    default = (
        directory.default_dev_username
        if settings.environment in _DEFAULT_PERSONA_ENVIRONMENTS
        else None
    )
    app.state.authentication = Authentication(settings.auth_mode, directory, default)


def _authentication(request: Request) -> Authentication:
    authentication: Authentication | None = getattr(request.app.state, "authentication", None)
    if authentication is None:
        raise RuntimeError("Authentication is not configured: call configure_authentication")
    return authentication


def _get_principal(request: Request, session: SessionDep) -> Principal:
    authentication = _authentication(request)
    if authentication.mode == "oidc":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC sign-in is not available yet. Use DMC_AUTH_MODE=dev locally.",
        )
    username = request.headers.get(DEV_USER_HEADER, "").strip()
    username = username or authentication.default_dev_username or ""
    if not username:
        raise UnauthenticatedError(f"Name a user in the {DEV_USER_HEADER} header.")
    principal = authentication.directory.principal_for(session, username)
    if principal is None:
        raise UnauthenticatedError(f"There is no active user called {username!r}.")
    return principal


PrincipalDep = Annotated[Principal, Depends(_get_principal)]


def _require_dev_auth(request: Request) -> None:
    if _authentication(request).mode != "dev":
        raise NotFoundError("Not found.")


# For dev-only routes: they answer 404 unless DMC_AUTH_MODE=dev.
DevAuthOnly = Depends(_require_dev_auth)


# --- Authorisation -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Permission:
    """An operation on a subject. `action` is the name it has in `allowed_actions`.

    Roles grant the operation; the subject's domain must also be in the principal's scope.
    """

    action: str
    roles: frozenset[Role]

    def __init__(self, action: str, roles: Iterable[Role]) -> None:
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "roles", frozenset(roles))


def can(principal: Principal, permission: Permission, domain_id: uuid.UUID | None = None) -> bool:
    return principal.has_any_role(permission.roles) and principal.in_scope(domain_id)


def require(
    principal: Principal, permission: Permission, domain_id: uuid.UUID | None = None
) -> None:
    """Raise PermissionDeniedError unless `principal` may do `permission` in `domain_id`."""
    if not principal.has_any_role(permission.roles):
        raise PermissionDeniedError(
            f"Your roles do not allow {permission.action}.",
            details={"action": permission.action},
        )
    if not principal.in_scope(domain_id):
        raise PermissionDeniedError(
            "This is outside the domains you are scoped to.",
            details={"action": permission.action},
        )


def allowed_actions(
    principal: Principal, permissions: Iterable[Permission], domain_id: uuid.UUID | None = None
) -> list[str]:
    """The `allowed_actions` of a response: every permission `require` would let through."""
    return sorted({p.action for p in permissions if can(principal, p, domain_id)})
