"""Service Tier: Manageable Governance Policy Engine.

Enables administrators and data stewards to configure, toggle, calibrate,
and execute dynamic compliance rules across catalog assets and control planes.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import delete, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import EntityNotFoundException, ValidationException
from app.models.asset import AssetHead, AssetVersion
from app.models.compliance import (
    ComplianceIssue,
    IssueSeverityEnum,
    IssueStatusEnum,
)
from app.models.policy_rule import (
    PolicyRule,
    PolicyRuleCategoryEnum,
    PolicyEnforcementModeEnum,
)


DEFAULT_BASELINE_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "MOV_001",
        "name": "Mandatory Transfer Integrity Pattern",
        "category": PolicyRuleCategoryEnum.DATA_MOVEMENT,
        "severity": IssueSeverityEnum.CRITICAL,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "INTEGRATION",
        "description": "All technical integrations between applications must bind at least one dataset and certify an approved transfer integrity verification mechanism (e.g., SHA-256 Checksum, Idempotent Deduplication, Two-Phase Commit).",
        "parameters": {
            "require_dataset": True,
            "forbidden_patterns": ["NONE_UNENFORCED"],
        },
        "remediation_guidance": "In the Workbench Data Movement control plane, bind at least one active dataset and select a certified transfer integrity pattern with implementation notes.",
    },
    {
        "rule_code": "STOR_001",
        "name": "Storage Retention Purge Attestation",
        "category": PolicyRuleCategoryEnum.STORAGE_RETENTION,
        "severity": IssueSeverityEnum.HIGH,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "STORAGE_CONTROL",
        "description": "Physical storage repositories and data stores must have automated purge cycles attested within their mandated retention window.",
        "parameters": {
            "max_purge_window_days": 90,
        },
        "remediation_guidance": "Execute the automated purge routine or certify purge logs in the Storage & Retention control plane.",
    },
    {
        "rule_code": "STOR_002",
        "name": "KMS Encryption at Rest Verification",
        "category": PolicyRuleCategoryEnum.STORAGE_RETENTION,
        "severity": IssueSeverityEnum.HIGH,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "STORAGE_CONTROL",
        "description": "Production storage repositories must configure an active Customer-Managed KMS Key (AWS KMS ARN, Azure Key Vault, or HashiCorp Vault transit key).",
        "parameters": {
            "allowed_algorithms": ["AES_256", "AES_GCM_256"],
        },
        "remediation_guidance": "Provide a valid KMS Key identifier and encryption algorithm in the storage repository configuration.",
    },
    {
        "rule_code": "PRIV_001",
        "name": "PII & Restricted Column Masking",
        "category": PolicyRuleCategoryEnum.PRIVACY_USAGE,
        "severity": IssueSeverityEnum.HIGH,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "PHYSICAL_COLUMN",
        "description": "Physical database columns tagged as PII or assigned HIGHLY_RESTRICTED / RESTRICTED tiers cannot have masking set to NONE.",
        "parameters": {
            "forbidden_strategies": ["NONE"],
            "allowed_strategies": ["FULL_REDACTION", "PARTIAL_MASK", "TOKENIZE", "HASH_SHA256"],
        },
        "remediation_guidance": "Navigate to the Schema Harvest control plane and assign an active masking strategy (Partial Mask, Tokenize, or Hash) to the column.",
    },
    {
        "rule_code": "PRIV_002",
        "name": "Authorized Consumer Entitlements",
        "category": PolicyRuleCategoryEnum.PRIVACY_USAGE,
        "severity": IssueSeverityEnum.MEDIUM,
        "enforcement_mode": PolicyEnforcementModeEnum.ADVISORY,
        "is_enabled": True,
        "default_sla_days": 30,
        "target_entity_type": "ASSET",
        "description": "Downstream applications consuming sensitive application datasets must hold an active, non-expired consumer entitlement.",
        "parameters": {
            "max_entitlement_validity_days": 365,
        },
        "remediation_guidance": "Submit a consumer entitlement request in the Privacy & Usage control plane stating business justification and region scope.",
    },
    {
        "rule_code": "DRIFT_001",
        "name": "Schema Drift & Unclassified Columns",
        "category": PolicyRuleCategoryEnum.SCHEMA_DRIFT,
        "severity": IssueSeverityEnum.HIGH,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "PHYSICAL_COLUMN",
        "description": "Automated schema harvests detecting new physical database columns flag ADDED_UNCLASSIFIED until classified by the application owner.",
        "parameters": {
            "auto_flag_pii": True,
        },
        "remediation_guidance": "Review harvested columns in the Schema Drift control plane, classify sensitivity, and tag PII status.",
    },
    {
        "rule_code": "CAT_DESC_MIN",
        "name": "Minimum Definition Length",
        "category": PolicyRuleCategoryEnum.CATALOG_METADATA,
        "severity": IssueSeverityEnum.MEDIUM,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "ASSET",
        "description": "Catalog assets and business terms must include a comprehensive definition meeting the minimum character threshold.",
        "parameters": {
            "min_chars": 50,
        },
        "remediation_guidance": "Edit the asset in Catalog and expand the description Markdown to at least 50 characters explaining business context.",
    },
    {
        "rule_code": "CAT_PII_TAG",
        "name": "Mandatory PII Classification",
        "category": PolicyRuleCategoryEnum.CATALOG_METADATA,
        "severity": IssueSeverityEnum.CRITICAL,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "ASSET",
        "description": "Every catalog asset must declare an explicit PII classification status (e.g. Yes/No, PII tier) to prevent untracked personal data.",
        "parameters": {
            "required": True,
        },
        "remediation_guidance": "Update the asset attributes to explicitly declare PII classification status.",
    },
    {
        "rule_code": "CAT_CONF_TIER",
        "name": "Confidentiality Tier Classification",
        "category": PolicyRuleCategoryEnum.CATALOG_METADATA,
        "severity": IssueSeverityEnum.HIGH,
        "enforcement_mode": PolicyEnforcementModeEnum.BLOCKING,
        "is_enabled": True,
        "default_sla_days": 14,
        "target_entity_type": "ASSET",
        "description": "Catalog assets must have an assigned data confidentiality tier (PUBLIC, INTERNAL, RESTRICTED, or HIGHLY_RESTRICTED).",
        "parameters": {
            "allowed_tiers": ["PUBLIC", "INTERNAL", "RESTRICTED", "HIGHLY_RESTRICTED"],
        },
        "remediation_guidance": "Assign an approved confidentiality classification tier to the asset.",
    },
]


class PolicyEngineService:
    """Core domain service for policy rule orchestration, evaluation, and management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_baseline_rules(self) -> int:
        """Seed default baseline governance rules if not present."""
        created_count = 0
        for rule_data in DEFAULT_BASELINE_RULES:
            stmt = select(PolicyRule).where(PolicyRule.rule_code == rule_data["rule_code"])
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                new_rule = PolicyRule(
                    id=uuid.uuid7(),
                    rule_code=rule_data["rule_code"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    category=rule_data["category"],
                    severity=rule_data["severity"],
                    enforcement_mode=rule_data["enforcement_mode"],
                    is_enabled=rule_data["is_enabled"],
                    default_sla_days=rule_data["default_sla_days"],
                    target_entity_type=rule_data["target_entity_type"],
                    parameters=rule_data["parameters"],
                    remediation_guidance=rule_data["remediation_guidance"],
                )
                self.session.add(new_rule)
                created_count += 1
        if created_count > 0:
            await self.session.commit()
        return created_count

    async def list_rules(
        self,
        category: Optional[str] = None,
        enforcement_mode: Optional[str] = None,
        enabled_only: bool = False,
    ) -> Dict[str, Any]:
        """List policy rules with summary stats."""
        # Ensure rules exist
        await self.ensure_baseline_rules()

        stmt = select(PolicyRule).order_by(PolicyRule.category.asc(), PolicyRule.rule_code.asc())
        if category:
            stmt = stmt.where(PolicyRule.category == category)
        if enforcement_mode:
            stmt = stmt.where(PolicyRule.enforcement_mode == enforcement_mode)
        if enabled_only:
            stmt = stmt.where(PolicyRule.is_enabled == True)

        res = await self.session.execute(stmt)
        rules = res.scalars().all()

        # Compute summary stats across all rules
        all_res = await self.session.execute(select(PolicyRule))
        all_rules = all_res.scalars().all()

        summary = {
            "total_rules": len(all_rules),
            "enabled_rules": sum(1 for r in all_rules if r.is_enabled),
            "disabled_rules": sum(1 for r in all_rules if not r.is_enabled),
            "blocking_rules": sum(1 for r in all_rules if r.is_enabled and r.enforcement_mode == PolicyEnforcementModeEnum.BLOCKING),
            "advisory_rules": sum(1 for r in all_rules if r.is_enabled and r.enforcement_mode == PolicyEnforcementModeEnum.ADVISORY),
            "by_category": {
                cat.value: sum(1 for r in all_rules if r.category == cat)
                for cat in PolicyRuleCategoryEnum
            },
        }

        serialized_rules = [
            {
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
            for r in rules
        ]

        return {
            "summary": summary,
            "rules": serialized_rules,
        }

    async def get_rule(self, rule_id: uuid.UUID) -> PolicyRule:
        """Fetch a policy rule by UUID."""
        stmt = select(PolicyRule).where(PolicyRule.id == rule_id)
        res = await self.session.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            raise EntityNotFoundException(f"Policy rule '{rule_id}' not found.")
        return rule

    async def update_rule(
        self,
        rule_id: uuid.UUID,
        is_enabled: Optional[bool] = None,
        enforcement_mode: Optional[PolicyEnforcementModeEnum] = None,
        severity: Optional[IssueSeverityEnum] = None,
        default_sla_days: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        remediation_guidance: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> PolicyRule:
        """Update configurable properties of a policy rule."""
        rule = await self.get_rule(rule_id)

        if is_enabled is not None:
            rule.is_enabled = is_enabled
        if enforcement_mode is not None:
            rule.enforcement_mode = enforcement_mode
            if enforcement_mode == PolicyEnforcementModeEnum.DISABLED:
                rule.is_enabled = False
            elif is_enabled is None:
                rule.is_enabled = True
        if severity is not None:
            rule.severity = severity
        if default_sla_days is not None:
            if default_sla_days < 1 or default_sla_days > 365:
                raise ValidationException("SLA days must be between 1 and 365.")
            rule.default_sla_days = default_sla_days
        if parameters is not None:
            rule.parameters = parameters
        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        if remediation_guidance is not None:
            rule.remediation_guidance = remediation_guidance
        if user_id:
            rule.updated_by = user_id

        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def toggle_rule(self, rule_id: uuid.UUID, enabled: bool) -> PolicyRule:
        """Quick toggle enable/disable state."""
        rule = await self.get_rule(rule_id)
        rule.is_enabled = enabled
        if not enabled:
            rule.enforcement_mode = PolicyEnforcementModeEnum.DISABLED
        elif rule.enforcement_mode == PolicyEnforcementModeEnum.DISABLED:
            rule.enforcement_mode = PolicyEnforcementModeEnum.BLOCKING
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def create_custom_rule(
        self,
        rule_code: str,
        name: str,
        description: str,
        category: PolicyRuleCategoryEnum,
        severity: IssueSeverityEnum,
        enforcement_mode: PolicyEnforcementModeEnum = PolicyEnforcementModeEnum.BLOCKING,
        default_sla_days: int = 14,
        target_entity_type: str = "ASSET",
        parameters: Optional[Dict[str, Any]] = None,
        remediation_guidance: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> PolicyRule:
        """Register a custom policy rule."""
        # Check rule_code uniqueness
        stmt = select(PolicyRule).where(PolicyRule.rule_code == rule_code.upper())
        res = await self.session.execute(stmt)
        if res.scalar_one_or_none():
            raise ValidationException(f"Rule code '{rule_code}' already exists.")

        rule = PolicyRule(
            id=uuid.uuid7(),
            rule_code=rule_code.upper(),
            name=name,
            description=description,
            category=category,
            severity=severity,
            enforcement_mode=enforcement_mode,
            is_enabled=enforcement_mode != PolicyEnforcementModeEnum.DISABLED,
            default_sla_days=default_sla_days,
            target_entity_type=target_entity_type,
            parameters=parameters or {},
            remediation_guidance=remediation_guidance,
            updated_by=user_id,
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def reset_to_defaults(self) -> int:
        """Reset all rules back to enterprise baseline defaults."""
        for default_rule in DEFAULT_BASELINE_RULES:
            stmt = select(PolicyRule).where(PolicyRule.rule_code == default_rule["rule_code"])
            res = await self.session.execute(stmt)
            rule = res.scalar_one_or_none()
            if rule:
                rule.name = default_rule["name"]
                rule.description = default_rule["description"]
                rule.category = default_rule["category"]
                rule.severity = default_rule["severity"]
                rule.enforcement_mode = default_rule["enforcement_mode"]
                rule.is_enabled = default_rule["is_enabled"]
                rule.default_sla_days = default_rule["default_sla_days"]
                rule.parameters = default_rule["parameters"]
                rule.remediation_guidance = default_rule["remediation_guidance"]
            else:
                self.session.add(PolicyRule(
                    id=uuid.uuid7(),
                    rule_code=default_rule["rule_code"],
                    name=default_rule["name"],
                    description=default_rule["description"],
                    category=default_rule["category"],
                    severity=default_rule["severity"],
                    enforcement_mode=default_rule["enforcement_mode"],
                    is_enabled=default_rule["is_enabled"],
                    default_sla_days=default_rule["default_sla_days"],
                    target_entity_type=default_rule["target_entity_type"],
                    parameters=default_rule["parameters"],
                    remediation_guidance=default_rule["remediation_guidance"],
                ))
        await self.session.commit()
        return len(DEFAULT_BASELINE_RULES)
