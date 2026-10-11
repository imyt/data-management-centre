import uuid
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@governance.com", "password": "password123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_pending_verifications(async_client: AsyncClient, auth_headers: dict):
    """Test retrieving queue of pending verifications for Data Stewards."""
    resp = await async_client.get("/api/v1/verifications", headers=auth_headers)
    assert resp.status_code == 200, f"Error: {resp.text}"
    data = resp.json()
    assert "summary" in data
    assert "integrations" in data
    assert "waivers" in data
    assert isinstance(data["summary"]["total_pending"], int)


@pytest.mark.asyncio
async def test_review_integration_lifecycle(async_client: AsyncClient, auth_headers: dict):
    """Test approving an integration transfer integrity pattern."""
    resp = await async_client.get("/api/v1/verifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    if not data["integrations"]:
        pytest.skip("No pending integrations in verification queue.")

    integ = data["integrations"][0]
    review_resp = await async_client.post(
        f"/api/v1/verifications/integrations/{integ['id']}/review",
        json={
            "approved": True,
            "decision_notes": "Verified cryptographic deduplication key hash with enterprise integration architecture team.",
        },
        headers=auth_headers,
    )
    assert review_resp.status_code == 200
    res_data = review_resp.json()
    assert res_data["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_review_exemption_lifecycle(async_client: AsyncClient, auth_headers: dict):
    """Test reviewing a compliance risk exemption waiver."""
    resp = await async_client.get("/api/v1/verifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    if not data["waivers"]:
        pytest.skip("No pending waivers in verification queue.")

    waiver = data["waivers"][0]
    review_resp = await async_client.post(
        f"/api/v1/verifications/exemptions/{waiver['id']}/review",
        json={
            "approved": True,
            "decision_notes": "Approved 45-day temporary waiver. Compensating VPC peering and Splunk SIEM controls confirmed active.",
        },
        headers=auth_headers,
    )
    assert review_resp.status_code == 200
    res_data = review_resp.json()
    assert res_data["status"] == "APPROVED"
