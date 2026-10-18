import pytest
from fastapi.testclient import TestClient

from app.core.auth import DEV_USER_HEADER, Role
from app.core.config import Settings
from app.core.db import Database
from app.main import create_app
from app.modules.identity.personas import CUSTOMER, FINANCE
from app.modules.identity.service import User


def test_me_is_the_persona_in_the_header(db_client: TestClient, personas: dict[str, User]) -> None:
    response = db_client.get("/api/v1/me", headers={DEV_USER_HEADER: "marcus.webb"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {
        "id": str(personas["marcus.webb"].id),
        "username": "marcus.webb",
        "display_name": "Marcus Webb",
        "roles": ["application_owner"],
        "domain_ids": sorted([str(CUSTOMER), str(FINANCE)]),
    }
    assert body["allowed_actions"] == []


def test_me_needs_a_known_user(db_client: TestClient, personas: dict[str, User]) -> None:
    unknown = db_client.get("/api/v1/me", headers={DEV_USER_HEADER: "nobody"})
    missing = db_client.get("/api/v1/me")

    assert unknown.status_code == 401
    assert unknown.json()["type"] == "urn:dmc:problem:unauthenticated"
    assert missing.status_code == 401  # no default persona in the test environment


def test_local_environment_falls_back_to_the_default_persona(
    database: Database, personas: dict[str, User]
) -> None:
    app = create_app(Settings(_env_file=None, environment="local"))
    app.state.database = database

    response = TestClient(app).get("/api/v1/me")

    assert response.json()["data"]["display_name"] == "Hannah Becker"
    assert response.json()["data"]["domain_ids"] is None


def test_dev_users_lists_one_persona_per_role(
    db_client: TestClient, personas: dict[str, User]
) -> None:
    response = db_client.get("/api/v1/dev/users")

    assert response.status_code == 200
    users = response.json()["data"]
    assert {role for user in users for role in user["roles"]} == {r.value for r in Role}
    assert response.json()["meta"]["total"] == len(users) == 7


@pytest.mark.parametrize("path", ["/api/v1/dev/users", "/api/v1/me"])
def test_oidc_mode_hides_dev_users_and_is_not_implemented(path: str, database: Database) -> None:
    app = create_app(Settings(_env_file=None, environment="test", auth_mode="oidc"))
    app.state.database = database

    status = TestClient(app, raise_server_exceptions=False).get(path).status_code

    assert status == (404 if path.endswith("dev/users") else 501)
