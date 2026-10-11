"""Tests for the Manageable Governance Policy Engine Service and Endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.policy_rule import (
    PolicyRule,
    PolicyRuleCategoryEnum,
    PolicyEnforcementModeEnum,
)
from app.models.compliance import IssueSeverityEnum
from app.services.policy_engine_service import PolicyEngineService


@pytest.mark.asyncio
async def test_policy_engine_baseline_seeding(db_session: AsyncSession):
    """Test that baseline rules seed cleanly with default parameters."""
    svc = PolicyEngineService(db_session)
    count = await svc.ensure_baseline_rules()
    res = await svc.list_rules()
    assert res["summary"]["total_rules"] >= 9
    assert res["summary"]["enabled_rules"] >= 9
    assert "MOV_001" in [r["rule_code"] for r in res["rules"]]
    assert "CAT_DESC_MIN" in [r["rule_code"] for r in res["rules"]]


@pytest.mark.asyncio
async def test_policy_engine_toggle_and_update(db_session: AsyncSession):
    """Test updating rule enforcement mode, SLA days, parameters and toggling."""
    svc = PolicyEngineService(db_session)
    await svc.ensure_baseline_rules()
    res = await svc.list_rules()
    target_rule = next(r for r in res["rules"] if r["rule_code"] == "CAT_DESC_MIN")

    # 1. Update rule
    import uuid
    rule_id = uuid.UUID(target_rule["id"])
    updated = await svc.update_rule(
        rule_id=rule_id,
        default_sla_days=7,
        parameters={"min_chars": 75},
        severity=IssueSeverityEnum.HIGH,
    )
    assert updated.default_sla_days == 7
    assert updated.parameters["min_chars"] == 75
    assert updated.severity == IssueSeverityEnum.HIGH

    # 2. Toggle off
    toggled_off = await svc.toggle_rule(rule_id=rule_id, enabled=False)
    assert toggled_off.is_enabled is False
    assert toggled_off.enforcement_mode == PolicyEnforcementModeEnum.DISABLED

    # 3. Toggle back on
    toggled_on = await svc.toggle_rule(rule_id=rule_id, enabled=True)
    assert toggled_on.is_enabled is True
    assert toggled_on.enforcement_mode == PolicyEnforcementModeEnum.BLOCKING


@pytest.mark.asyncio
async def test_policy_engine_custom_rule_and_reset(db_session: AsyncSession):
    """Test creating a custom rule and resetting to defaults."""
    svc = PolicyEngineService(db_session)
    await svc.ensure_baseline_rules()

    # Create custom rule with unique code
    import uuid
    code = f"CUSTOM_TEST_{uuid.uuid4().hex[:6].upper()}"
    custom = await svc.create_custom_rule(
        rule_code=code,
        name="Mandatory Data Retention Label",
        description="Every dataset must have an explicit retention tier label.",
        category=PolicyRuleCategoryEnum.STORAGE_RETENTION,
        severity=IssueSeverityEnum.MEDIUM,
        default_sla_days=21,
    )
    assert custom.rule_code == code
    assert custom.default_sla_days == 21

    # Reset to defaults
    reset_count = await svc.reset_to_defaults()
    assert reset_count >= 9
