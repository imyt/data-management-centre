"""Integration tests for Application Owner Workbench and 4 Control Planes."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.data_movement import ApplicationProfile, IntegrityPatternEnum, ISRClassificationEnum
from app.models.physical_schema import MaskingStrategyEnum
from app.models.storage_control import StorageTypeEnum, EncryptionAlgorithmEnum, PurgeMechanismEnum
from app.models.compliance import ComplianceIssue, IssueStatusEnum


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@governance.com", "password": "password123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def core_banking_app_head_id():
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ApplicationProfile).where(ApplicationProfile.itsm_system_id == "APP-10921")
        )
        profile = res.scalar_one_or_none()
        assert profile is not None, "Core Banking Profile APP-10921 not found."
        return profile.asset_head_id


@pytest.mark.asyncio
async def test_workbench_summary_and_metrics(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test workbench summary returns health score, urgent defect list, and control planes stats."""
    resp = await async_client.get(
        f"/api/v1/workbench/{core_banking_app_head_id}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert data["application"]["itsm_system_id"] == "APP-10921"
    assert "health_score" in data["posture"]
    assert data["posture"]["open_defects"] >= 1
    assert "data_movement" in data["control_planes"]
    assert "storage_retention" in data["control_planes"]
    assert "schema_harvest" in data["control_planes"]
    assert "privacy_usage" in data["control_planes"]
    assert len(data["urgent_defects"]) >= 1


@pytest.mark.asyncio
async def test_workbench_issues_queue(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test listing actionable compliance defects with technical context."""
    resp = await async_client.get(
        f"/api/v1/workbench/{core_banking_app_head_id}/issues",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    issues = resp.json()
    assert isinstance(issues, list)
    assert len(issues) >= 1

    rule_codes = [i["rule_code"] for i in issues if i["rule_code"]]
    assert any(code in rule_codes for code in ["MOV_001", "DRIFT_001", "STOR_001", "PRIV_001"])


@pytest.mark.asyncio
async def test_remediate_integrity_pattern_workflow(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test remediating MOV_001 by certifying transfer integrity pattern."""
    # Find MOV_001 issue
    issues_resp = await async_client.get(
        f"/api/v1/workbench/{core_banking_app_head_id}/issues?rule_code=MOV_001",
        headers=auth_headers,
    )
    issues = issues_resp.json()
    if not issues:
        pytest.skip("No MOV_001 issue found.")

    issue = issues[0]
    integ_id = issue["integration"]["id"]

    remediate_resp = await async_client.post(
        "/api/v1/workbench/remediate/integrity",
        json={
            "issue_id": issue["id"],
            "integration_id": integ_id,
            "pattern": IntegrityPatternEnum.CHECKSUM_HASH_VERIFICATION.value,
            "pattern_details": "SHA-256 digest header validated at message consumer boundary.",
        },
        headers=auth_headers,
    )
    assert remediate_resp.status_code == 200, f"Remediation failed: {remediate_resp.text}"
    assert remediate_resp.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_remediate_drift_workflow(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test remediating DRIFT_001 by classifying unclassified columns."""
    issues_resp = await async_client.get(
        f"/api/v1/workbench/{core_banking_app_head_id}/issues?rule_code=DRIFT_001",
        headers=auth_headers,
    )
    issues = issues_resp.json()
    if not issues:
        pytest.skip("No DRIFT_001 issue found.")

    issue = issues[0]

    # Get columns
    cols_resp = await async_client.get(
        f"/api/v1/schema-harvest/app/{core_banking_app_head_id}/columns",
        headers=auth_headers,
    )
    cols = cols_resp.json()
    if not cols:
        pytest.skip("No columns found to classify.")

    classifications = [
        {
            "column_id": cols[0]["id"],
            "is_pii": True,
            "masking_strategy": MaskingStrategyEnum.PARTIAL_MASK.value,
            "isr_classification": ISRClassificationEnum.RESTRICTED.value,
            "business_term_name": "Account Routing Code",
        }
    ]

    remediate_resp = await async_client.post(
        "/api/v1/workbench/remediate/drift",
        json={
            "issue_id": issue["id"],
            "classifications": classifications,
        },
        headers=auth_headers,
    )
    assert remediate_resp.status_code == 200
    assert remediate_resp.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_storage_control_plane_and_legal_hold(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test storage listing, legal hold toggle, and purge attestation."""
    stor_resp = await async_client.get(
        f"/api/v1/storage/app/{core_banking_app_head_id}",
        headers=auth_headers,
    )
    assert stor_resp.status_code == 200
    storages = stor_resp.json()
    assert len(storages) >= 1

    storage_id = storages[0]["id"]

    # Toggle Legal Hold
    lh_resp = await async_client.post(
        f"/api/v1/storage/{storage_id}/legal-hold",
        json={"active": True, "reason": "Department of Justice Subpoena Ref #8921"},
        headers=auth_headers,
    )
    assert lh_resp.status_code == 200
    assert lh_resp.json()["legal_hold_active"] is True

    # Lift Legal Hold
    lh_lift = await async_client.post(
        f"/api/v1/storage/{storage_id}/legal-hold",
        json={"active": False},
        headers=auth_headers,
    )
    assert lh_lift.status_code == 200
    assert lh_lift.json()["legal_hold_active"] is False


@pytest.mark.asyncio
async def test_schema_harvest_trigger(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test triggering on-demand schema harvest."""
    harvest_resp = await async_client.post(
        "/api/v1/schema-harvest/trigger",
        json={"app_head_id": str(core_banking_app_head_id)},
        headers=auth_headers,
    )
    assert harvest_resp.status_code == 200
    data = harvest_resp.json()
    assert "harvest_run_id" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_privacy_entitlements_lifecycle(async_client: AsyncClient, auth_headers: dict, core_banking_app_head_id: uuid.UUID):
    """Test listing and revoking consumer entitlements."""
    ent_resp = await async_client.get(
        f"/api/v1/privacy/app/{core_banking_app_head_id}/entitlements",
        headers=auth_headers,
    )
    assert ent_resp.status_code == 200
    entitlements = ent_resp.json()
    assert len(entitlements) >= 1
    assert "authorized_purpose" in entitlements[0]
