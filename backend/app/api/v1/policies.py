"""API Router for Manageable Governance Policy Engine."""
from typing import Annotated, Any, Dict, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.domain.exceptions import EntityNotFoundException, ValidationException
from app.models.compliance import IssueSeverityEnum
from app.models.policy_rule import PolicyRuleCategoryEnum, PolicyEnforcementModeEnum
from app.models.user import User
from app.services.policy_engine_service import PolicyEngineService
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/policies", tags=["Policy Engine & Rules"])


def get_policy_service(db: Annotated[AsyncSession, Depends(get_db)]) -> PolicyEngineService:
    return PolicyEngineService(db)


def get_compliance_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ComplianceService:
    return ComplianceService(db)


# -------------------------------------------------------------------------
# Request / Response Schemas
# -------------------------------------------------------------------------

class UpdatePolicyRuleRequest(BaseModel):
    is_enabled: Optional[bool] = None
    enforcement_mode: Optional[PolicyEnforcementModeEnum] = None
    severity: Optional[IssueSeverityEnum] = None
    default_sla_days: Optional[int] = Field(None, ge=1, le=365)
    parameters: Optional[Dict[str, Any]] = None
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    remediation_guidance: Optional[str] = None


class TogglePolicyRuleRequest(BaseModel):
    is_enabled: bool


class CreateCustomPolicyRuleRequest(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10)
    category: PolicyRuleCategoryEnum
    severity: IssueSeverityEnum = IssueSeverityEnum.MEDIUM
    enforcement_mode: PolicyEnforcementModeEnum = PolicyEnforcementModeEnum.BLOCKING
    default_sla_days: int = Field(14, ge=1, le=365)
    target_entity_type: str = "ASSET"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    remediation_guidance: Optional[str] = None


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------

@router.get("/rules")
async def list_policy_rules(
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    category: Optional[str] = Query(None, description="Filter by category"),
    enforcement_mode: Optional[str] = Query(None, description="Filter by enforcement mode"),
    enabled_only: bool = Query(False, description="Filter only enabled rules"),
) -> Dict[str, Any]:
    """List all manageable governance policy rules with summary metrics."""
    return await service.list_rules(
        category=category,
        enforcement_mode=enforcement_mode,
        enabled_only=enabled_only,
    )


@router.get("/rules/{rule_id}")
async def get_policy_rule(
    rule_id: uuid.UUID,
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Retrieve details of a single policy rule."""
    try:
        r = await service.get_rule(rule_id)
        return {
            "id": str(r.id),
            "rule_code": r.rule_code,
            "name": r.name,
            "description": r.description,
            "category": r.category.value,
            "severity": r.severity.value,
            "enforcement_mode": r.enforcement_mode.value,
            "is_enabled": r.is_enabled,
            "default_sla_days": r.default_sla_days,
            "target_entity_type": r.target_entity_type,
            "parameters": r.parameters,
            "remediation_guidance": r.remediation_guidance,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_policy_rule(
    rule_id: uuid.UUID,
    req: UpdatePolicyRuleRequest,
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Update rule configuration (enforcement mode, SLA days, severity, parameters)."""
    try:
        r = await service.update_rule(
            rule_id=rule_id,
            is_enabled=req.is_enabled,
            enforcement_mode=req.enforcement_mode,
            severity=req.severity,
            default_sla_days=req.default_sla_days,
            parameters=req.parameters,
            name=req.name,
            description=req.description,
            remediation_guidance=req.remediation_guidance,
            user_id=current_user.id,
        )
        return {
            "id": str(r.id),
            "rule_code": r.rule_code,
            "name": r.name,
            "category": r.category.value,
            "severity": r.severity.value,
            "enforcement_mode": r.enforcement_mode.value,
            "is_enabled": r.is_enabled,
            "default_sla_days": r.default_sla_days,
            "parameters": r.parameters,
            "remediation_guidance": r.remediation_guidance,
            "updated_at": r.updated_at.isoformat(),
        }
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/rules/{rule_id}/toggle")
async def toggle_policy_rule(
    rule_id: uuid.UUID,
    req: TogglePolicyRuleRequest,
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """One-click toggle to enable or disable a policy rule."""
    try:
        r = await service.toggle_rule(rule_id=rule_id, enabled=req.is_enabled)
        return {
            "id": str(r.id),
            "rule_code": r.rule_code,
            "is_enabled": r.is_enabled,
            "enforcement_mode": r.enforcement_mode.value,
        }
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_custom_policy_rule(
    req: CreateCustomPolicyRuleRequest,
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Create a new custom metadata or control plane governance rule."""
    try:
        r = await service.create_custom_rule(
            rule_code=req.rule_code,
            name=req.name,
            description=req.description,
            category=req.category,
            severity=req.severity,
            enforcement_mode=req.enforcement_mode,
            default_sla_days=req.default_sla_days,
            target_entity_type=req.target_entity_type,
            parameters=req.parameters,
            remediation_guidance=req.remediation_guidance,
            user_id=current_user.id,
        )
        return {
            "id": str(r.id),
            "rule_code": r.rule_code,
            "name": r.name,
            "category": r.category.value,
            "severity": r.severity.value,
            "enforcement_mode": r.enforcement_mode.value,
            "is_enabled": r.is_enabled,
            "default_sla_days": r.default_sla_days,
            "parameters": r.parameters,
            "created_at": r.created_at.isoformat(),
        }
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rules/reset-defaults")
async def reset_policy_rules_to_defaults(
    service: Annotated[PolicyEngineService, Depends(get_policy_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    """Restore all baseline governance policy rules to factory enterprise defaults."""
    count = await service.reset_to_defaults()
    return {
        "status": "success",
        "message": f"Successfully reset {count} baseline governance rules to enterprise defaults.",
    }


@router.post("/evaluate")
async def evaluate_policy_rules(
    compliance_service: Annotated[ComplianceService, Depends(get_compliance_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    domain_id: Optional[uuid.UUID] = Query(None, description="Optional domain scope"),
) -> Dict[str, Any]:
    """Trigger real-time evaluation of all active policy rules across catalog assets."""
    res = await compliance_service.scan_policies(actor_id=current_user.id, domain_id=domain_id)
    return {
        "status": "success",
        "new_issues_count": res.new_issues_count,
        "existing_issues_count": res.existing_issues_count,
        "scanned_at": res.scanned_at.isoformat(),
        "total_issues_identified": len(res.issues),
    }
