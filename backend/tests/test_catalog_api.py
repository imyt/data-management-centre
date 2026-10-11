import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_metamodel_asset_types(async_client: AsyncClient):
    """Test metamodel endpoint returns seeded asset types."""
    resp = await async_client.get("/api/v1/metamodel/asset-types")
    assert resp.status_code == 200
    types = resp.json()
    codes = [t["code"] for t in types]
    assert "BUSINESS_TERM" in codes
    assert "APPLICATION" in codes
    assert "DATA_POLICY" in codes


@pytest.mark.asyncio
async def test_create_and_query_asset(async_client: AsyncClient):
    """Test full cycle of authentication, creating an asset head with draft, and querying it."""
    # 1. Login as Data Steward
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "steward@governance.com", "password": "password123"}
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Domain and AssetType
    dom_resp = await async_client.get("/api/v1/domains")
    assert dom_resp.status_code == 200
    domain_id = dom_resp.json()[0]["id"]

    types_resp = await async_client.get("/api/v1/metamodel/asset-types")
    assert types_resp.status_code == 200
    type_id = [t["id"] for t in types_resp.json() if t["code"] == "BUSINESS_TERM"][0]

    # 3. Create Asset Head & Initial Draft
    create_resp = await async_client.post(
        "/api/v1/assets",
        json={
            "domain_id": domain_id,
            "asset_type_id": type_id,
            "name": "Adjusted EBITDA",
            "description_markdown": "Earnings before interest, taxes, depreciation, amortization with standardized GAAP adjustments.",
            "attributes_payload": {"CONFIDENTIALITY": "INTERNAL", "PII": False}
        },
        headers=headers
    )
    assert create_resp.status_code == 201, f"Asset create failed: {create_resp.text}"
    created_asset = create_resp.json()
    assert created_asset["active_draft_version"] is not None
    assert created_asset["active_draft_version"]["name"] == "Adjusted EBITDA"
    assert created_asset["active_draft_version"]["version_number"] == 1
    assert created_asset["active_draft_version"]["status"] == "DRAFT"

    # 4. Search Asset by Trigram / Substring
    search_resp = await async_client.get("/api/v1/assets?search=EBITDA")
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert any(a["id"] == created_asset["id"] for a in results)
