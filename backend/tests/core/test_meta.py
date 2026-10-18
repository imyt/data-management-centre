import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.contract import contract_hash
from app.core.meta import resolve_commit
from app.main import create_app

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "openapi.json"


def test_meta_reports_the_build(client: TestClient) -> None:
    response = client.get("/api/v1/meta")
    body = response.json()

    assert response.status_code == 200
    assert body["environment"] == "test"
    assert body["version"] == client.app.version  # type: ignore[attr-defined]
    assert set(body) == {"environment", "version", "commit", "contract"}


def test_contract_is_the_hash_of_the_committed_spec(client: TestClient) -> None:
    contract = client.get("/api/v1/meta").json()["contract"]

    assert re.fullmatch(r"sha256:[0-9a-f]{64}", contract)
    assert contract == contract_hash(CONTRACT.read_text(encoding="utf-8"))


def test_contract_hash_ignores_line_endings() -> None:
    assert contract_hash('{\r\n  "a": 1\r\n}\n') == contract_hash('{\n  "a": 1\n}\n')
    # The value the frontend's test pins for the same text (frontend/contract-hash.test.ts).
    assert contract_hash("{}\n") == (
        "sha256:ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"
    )


def test_commit_comes_from_dmc_commit() -> None:
    app = create_app(Settings(_env_file=None, environment="test", commit="24a18c3"))

    assert TestClient(app).get("/api/v1/meta").json()["commit"] == "24a18c3"


def test_commit_falls_back_to_git_or_unknown() -> None:
    commit = resolve_commit(None)

    assert commit == "unknown" or re.fullmatch(r"[0-9a-f]{7,}", commit)
