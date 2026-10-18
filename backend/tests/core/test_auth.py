import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import (
    DEV_USER_HEADER,
    DevAuthOnly,
    Permission,
    Principal,
    PrincipalDep,
    Role,
    allowed_actions,
    can,
    configure_authentication,
    require,
)
from app.core.config import Settings
from app.core.errors import PermissionDeniedError
from app.core.handlers import register_error_handlers

FINANCE = uuid.uuid4()
SALES = uuid.uuid4()

OWNER = Principal(uuid.uuid4(), "Ada Owner", frozenset({Role.DATA_OWNER}), frozenset({FINANCE}))
GOVERNANCE = Principal(uuid.uuid4(), "Gil Governance", frozenset({Role.GOVERNANCE}), None)
AUDITOR = Principal(uuid.uuid4(), "Aud Itor", frozenset({Role.AUDITOR}), None)

EDIT = Permission("edit", {Role.DATA_OWNER, Role.GOVERNANCE})
ACCEPT_RISK = Permission("accept_risk", {Role.DATA_OWNER})


class FakeDirectory:
    default_dev_username = "gil"

    def __init__(self) -> None:
        self.users = {"ada": OWNER, "gil": GOVERNANCE}

    def principal_for(self, session: object, username: str) -> Principal | None:
        return self.users.get(username)


class FakeDatabase:
    @contextmanager
    def transaction(self) -> Iterator[None]:
        yield None


def _client(**settings: object) -> TestClient:
    router = APIRouter()

    @router.get("/whoami", operation_id="whoami")
    def whoami(principal: PrincipalDep) -> dict[str, str]:
        return {"actor": principal.actor, "name": principal.display_name}

    @router.get("/dev-only", operation_id="devOnly", dependencies=[DevAuthOnly])
    def dev_only() -> dict[str, bool]:
        return {"ok": True}

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.state.database = FakeDatabase()
    configure_authentication(app, Settings(_env_file=None, **settings), FakeDirectory())  # type: ignore[arg-type]
    return TestClient(app, raise_server_exceptions=False)


def test_actor_names_the_user() -> None:
    assert OWNER.actor == f"user:{OWNER.user_id}"


def test_dev_header_picks_the_user() -> None:
    response = _client().get("/whoami", headers={DEV_USER_HEADER: "ada"})

    assert response.json() == {"actor": OWNER.actor, "name": "Ada Owner"}


@pytest.mark.parametrize("environment", ["local", "dev"])
def test_missing_header_is_the_default_persona_locally(environment: str) -> None:
    response = _client(environment=environment, database_url="postgresql://x").get("/whoami")

    assert response.json()["name"] == "Gil Governance"


def test_missing_header_is_unauthenticated_in_test() -> None:
    response = _client(environment="test").get("/whoami")

    assert response.status_code == 401
    assert response.json()["type"] == "urn:dmc:problem:unauthenticated"


def test_unknown_user_is_unauthenticated() -> None:
    response = _client().get("/whoami", headers={DEV_USER_HEADER: "mallory"})

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert "mallory" in response.json()["detail"]


def test_oidc_is_not_implemented_yet() -> None:
    client = _client(auth_mode="oidc")

    assert client.get("/whoami").status_code == 501
    assert client.get("/dev-only").status_code == 404
    assert _client().get("/dev-only").status_code == 200


def test_roles_and_scope_decide_permissions() -> None:
    assert can(OWNER, EDIT, FINANCE)
    assert not can(OWNER, EDIT, SALES)
    assert can(OWNER, EDIT)  # a subject without a domain
    assert can(GOVERNANCE, EDIT, SALES)  # None scope means every domain
    assert not can(AUDITOR, EDIT, FINANCE)


def test_require_explains_the_refusal() -> None:
    require(OWNER, ACCEPT_RISK, FINANCE)
    with pytest.raises(PermissionDeniedError, match="roles"):
        require(GOVERNANCE, ACCEPT_RISK, FINANCE)
    with pytest.raises(PermissionDeniedError, match="outside the domains"):
        require(OWNER, ACCEPT_RISK, SALES)


def test_allowed_actions_follow_the_same_rules() -> None:
    assert allowed_actions(OWNER, [EDIT, ACCEPT_RISK], FINANCE) == ["accept_risk", "edit"]
    assert allowed_actions(OWNER, [EDIT, ACCEPT_RISK], SALES) == []
    assert allowed_actions(GOVERNANCE, [EDIT, ACCEPT_RISK], SALES) == ["edit"]
    assert allowed_actions(AUDITOR, [EDIT, ACCEPT_RISK]) == []
