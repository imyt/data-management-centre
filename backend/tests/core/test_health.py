from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.config import Settings
from app.core.db import Database
from app.main import create_app


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_the_database_answers(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_not_ready_without_a_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "No database is configured."


def test_not_ready_when_the_database_is_unreachable() -> None:
    app = create_app(Settings(_env_file=None, environment="test"))
    unreachable = create_engine(
        "postgresql+psycopg://nobody:x@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    app.state.database = Database(unreachable)

    response = TestClient(app, raise_server_exceptions=False).get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "The database is not reachable."
