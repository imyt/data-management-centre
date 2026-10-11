import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_version_lifecycle_diff_and_concurrency(async_client: AsyncClient):
    """Verify the entire Phase 2 Versioning, Lock, Diff, and Publication Engine."""
    # 1. Login as Data Steward (Sarah Chen)
    steward_auth = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "steward@governance.com", "password": "password123"}
    )
    steward_token = steward_auth.json()["access_token"]
    steward_headers = {"Authorization": f"Bearer {steward_token}"}

    # 2. Login as Business Owner (David Vance)
    owner_auth = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "business.owner@governance.com", "password": "password123"}
    )
    owner_token = owner_auth.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 3. Get Metamodel & Domain
    dom_resp = await async_client.get("/api/v1/domains")
    domain_id = dom_resp.json()[0]["id"]
    types_resp = await async_client.get("/api/v1/metamodel/asset-types")
    term_type_id = [t["id"] for t in types_resp.json() if t["code"] == "BUSINESS_TERM"][0]

    # 4. Create Asset Head & Initial Draft (v1)
    create_resp = await async_client.post(
        "/api/v1/assets",
        json={
            "domain_id": domain_id,
            "asset_type_id": term_type_id,
            "name": "Customer Lifetime Value (LTV)",
            "description_markdown": "Initial definition of customer lifetime revenue projection.",
            "attributes_payload": {"CONFIDENTIALITY": "INTERNAL", "PII": False}
        },
        headers=steward_headers
    )
    assert create_resp.status_code == 201
    head_id = create_resp.json()["id"]

    # 5. Publish v1
    pub_v1_resp = await async_client.post(
        f"/api/v1/assets/{head_id}/publish",
        headers=owner_headers
    )
    assert pub_v1_resp.status_code == 200
    v1_data = pub_v1_resp.json()
    assert v1_data["status"] == "PUBLISHED"
    assert v1_data["version_number"] == 1

    # 6. Verify Head now points to published v1 and active_draft is None
    head_check = await async_client.get(f"/api/v1/assets/{head_id}")
    assert head_check.json()["published_version_id"] == v1_data["id"]
    assert head_check.json()["active_draft_version_id"] is None
    assert head_check.json()["locked_by_user_id"] is None

    # 7. Steward forks a new working draft (v2-DRAFT)
    draft_v2_resp = await async_client.post(
        f"/api/v1/assets/{head_id}/draft",
        headers=steward_headers
    )
    assert draft_v2_resp.status_code == 200
    v2_draft = draft_v2_resp.json()
    assert v2_draft["version_number"] == 2
    assert v2_draft["status"] == "DRAFT"

    # 8. Test Concurrency Lock: Business Owner attempts to edit or fork the draft
    # Business Owner attempts to update draft while locked by Steward
    conflict_resp = await async_client.put(
        f"/api/v1/assets/{head_id}/draft",
        json={"name": "Hijacked Name"},
        headers=owner_headers
    )
    assert conflict_resp.status_code == 403
    assert "You do not hold the active draft lock" in conflict_resp.json()["detail"]

    # 9. Steward updates draft with expanded Markdown and altered attributes
    update_resp = await async_client.put(
        f"/api/v1/assets/{head_id}/draft",
        json={
            "name": "Customer Lifetime Value (CLV/LTV)",
            "description_markdown": "Enhanced definition incorporating gross margin multipliers and churn rates.",
            "attributes_payload": {"CONFIDENTIALITY": "RESTRICTED", "PII": True, "CRITICALITY": "HIGH"}
        },
        headers=steward_headers
    )
    assert update_resp.status_code == 200

    # 10. Generate Visual Diff between v1 (Published) and v2 (Draft)
    diff_resp = await async_client.get(f"/api/v1/assets/{head_id}/diff")
    assert diff_resp.status_code == 200
    diff = diff_resp.json()
    assert diff["has_changes"] is True
    assert diff["name_diff"]["changed"] is True
    assert diff["name_diff"]["old_name"] == "Customer Lifetime Value (LTV)"
    assert diff["name_diff"]["new_name"] == "Customer Lifetime Value (CLV/LTV)"
    assert diff["description_diff"]["has_changes"] is True

    # Check attribute changes
    attr_changes = {a["attribute_code"]: a for a in diff["attributes_diff"]}
    assert attr_changes["CONFIDENTIALITY"]["change_type"] == "MODIFIED"
    assert attr_changes["CONFIDENTIALITY"]["old_value"] == "INTERNAL"
    assert attr_changes["CONFIDENTIALITY"]["new_value"] == "RESTRICTED"
    assert attr_changes["PII"]["change_type"] == "MODIFIED"
    assert attr_changes["CRITICALITY"]["change_type"] == "ADDED"

    # 11. Publish v2
    pub_v2_resp = await async_client.post(
        f"/api/v1/assets/{head_id}/publish",
        headers=owner_headers
    )
    assert pub_v2_resp.status_code == 200
    v2_data = pub_v2_resp.json()
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "PUBLISHED"

    # 12. Audit History: verify v1 is now SUPERSEDED and v2 is PUBLISHED
    history_resp = await async_client.get(f"/api/v1/assets/{head_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 2
    assert history[0]["version_number"] == 2
    assert history[0]["status"] == "PUBLISHED"
    assert history[1]["version_number"] == 1
    assert history[1]["status"] == "SUPERSEDED"
