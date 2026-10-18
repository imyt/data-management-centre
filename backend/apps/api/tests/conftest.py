import pytest
from fastapi.testclient import TestClient

from dmc_api.main import create_app
from dmc_api.settings import Settings


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(_env_file=None, environment="test"))
    return TestClient(app, raise_server_exceptions=False)
