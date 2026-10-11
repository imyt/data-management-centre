import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health endpoint reports healthy with PostgreSQL 18."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "PostgreSQL 18" in data["database"]
    assert "Zero-Redis" in data["cache"]


@pytest.mark.asyncio
async def test_login_success_and_me(async_client: AsyncClient):
    """Test login with seeded admin credentials and retrieve current user via /me."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@governance.com", "password": "password123"}
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "admin@governance.com"

    # Use token to call /me
    token = token_data["access_token"]
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@governance.com"
    assert me_data["is_superuser"] is True


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """Test login rejects invalid password with 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@governance.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
