"""Service Tier: Cohesive domain service managing compliance scans & remediation.

Detects data quality anomalies, unclassified PII, missing confidentiality tiers,
tracks remediation lifecycles, and executes one-click automated fixes.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.compliance import IssueSeverity, IssueStatus
from app.domain.exceptions import EntityNotFoundException, ValidationException
from app.models.asset import AssetHead, AssetVersion
from app.models.compliance import (
    ComplianceIssue,
    IssueSeverityEnum,
    IssueStatusEnum,
)
from app.schemas.compliance import (
    ComplianceIssueRead,
    ComplianceScanResponse,
)


class ComplianceService:
    """Cohesive business logic service for policy scans and automated remediation."""

    DEFAULT_SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    async def get_issue(self, issue_id: uuid.UUID) -> ComplianceIssue:
        """Fetch issue with associated asset head and owner."""
        stmt = (
            select(ComplianceIssue)
            .options(
                selectinload(ComplianceIssue.target_asset_head),
                selectinload(ComplianceIssue.app_owner),
                selectinload(ComplianceIssue.assigned_steward),
            )
            .where(ComplianceIssue.id == issue_id)
        )
        result = await self.db.execute(stmt)
        issue = result.scalar_one_or_none()
        if not issue:
            raise EntityNotFoundException(f"Compliance issue '{issue_id}' not found.")
        return issue

    async def list_issues(
        self,
        domain_id: Optional[uuid.UUID] = None,
        asset_id: Optional[uuid.UUID] = None,
        severity: Optional[IssueSeverity] = None,
        status: Optional[IssueStatus] = None,
        limit: int = 100,
    ) -> List[ComplianceIssue]:
        """List compliance issues with optional domain, severity, and status filters."""
        stmt = (
            select(ComplianceIssue)
            .options(
                selectinload(ComplianceIssue.target_asset_head),
                selectinload(ComplianceIssue.app_owner),
                selectinload(ComplianceIssue.assigned_steward),
            )
            .order_by(ComplianceIssue.created_at.desc())
        )

        if asset_id:
            stmt = stmt.where(ComplianceIssue.target_asset_head_id == asset_id)

        if severity:
            stmt = stmt.where(ComplianceIssue.severity == IssueSeverityEnum(severity.value))

        if status:
            stmt = stmt.where(ComplianceIssue.status == IssueStatusEnum(status.value))

        if domain_id:
            stmt = stmt.join(ComplianceIssue.target_asset_head).where(
                AssetHead.domain_id == domain_id
            )

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Policy Scans & Auto-Remediation
    # -------------------------------------------------------------------------

    async def scan_policies(
        self,
        actor_id: Optional[uuid.UUID] = None,
        domain_id: Optional[uuid.UUID] = None,
    ) -> ComplianceScanResponse:
        """Run automated scan over catalog assets, generating actionable issues."""
        actor = actor_id or self.DEFAULT_SYSTEM_ACTOR_ID
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=14)

        # 1. Fetch asset heads
        stmt = (
            select(AssetHead)
            .options(
                selectinload(AssetHead.published_version),
                selectinload(AssetHead.active_draft_version),
            )
        )
        if domain_id:
            stmt = stmt.where(AssetHead.domain_id == domain_id)

        result = await self.db.execute(stmt)
        heads = list(result.scalars().all())

        new_count = 0
        existing_count = 0
        created_or_found: List[ComplianceIssue] = []

        # Load active policy rules from dynamic policy engine
        from app.services.policy_engine_service import PolicyEngineService
        from app.models.policy_rule import PolicyRule
        policy_svc = PolicyEngineService(self.db)
        await policy_svc.ensure_baseline_rules()
        rules_res = await self.db.execute(select(PolicyRule).where(PolicyRule.is_enabled == True))
        active_rules = {r.rule_code: r for r in rules_res.scalars().all()}

        for head in heads:
            version = head.published_version or head.active_draft_version
            if not version:
                continue

            violations: List[Tuple[str, str, str, IssueSeverityEnum, int]] = []

            # Rule 1: Thin Description (CAT_DESC_MIN)
            if "CAT_DESC_MIN" in active_rules:
                cat_desc_rule = active_rules["CAT_DESC_MIN"]
                min_chars = int(cat_desc_rule.parameters.get("min_chars", 50))
                desc = (version.description_markdown or "").strip()
                if not desc or len(desc) < min_chars:
                    violations.append((
                        cat_desc_rule.rule_code,
                        f"Thin Description (<{min_chars} chars)",
                        f"Asset '{version.name}' has no detailed description or definition is too brief ({len(desc)} characters; minimum mandated is {min_chars}).",
                        cat_desc_rule.severity,
                        cat_desc_rule.default_sla_days,
                    ))

            # Rule 2: Unclassified PII (CAT_PII_TAG)
            if "CAT_PII_TAG" in active_rules:
                cat_pii_rule = active_rules["CAT_PII_TAG"]
                attrs = {k.lower(): v for k, v in (version.attributes_payload or {}).items()}
                pii_val = None
                for pii_key in ("pii", "pii_classification", "contains_pii", "has_pii", "pii_type"):
                    if pii_key in attrs:
                        pii_val = attrs[pii_key]
                        break
                if pii_val is None or str(pii_val).strip().upper() in ("", "UNCLASSIFIED", "UNKNOWN", "NOT_SET"):
                    violations.append((
                        cat_pii_rule.rule_code,
                        "Unclassified PII Status",
                        f"Asset '{version.name}' lacks mandatory Personal Identifiable Information (PII) classification tag.",
                        cat_pii_rule.severity,
                        cat_pii_rule.default_sla_days,
                    ))

            # Rule 3: Missing Confidentiality (CAT_CONF_TIER)
            if "CAT_CONF_TIER" in active_rules:
                cat_conf_rule = active_rules["CAT_CONF_TIER"]
                attrs = {k.lower(): v for k, v in (version.attributes_payload or {}).items()}
                conf_val = None
                for conf_key in ("confidentiality", "confidentiality_tier", "classification", "security_classification"):
                    if conf_key in attrs:
                        conf_val = attrs[conf_key]
                        break
                if conf_val is None or str(conf_val).strip().upper() in ("", "UNCLASSIFIED", "UNKNOWN", "NOT_SET"):
                    violations.append((
                        cat_conf_rule.rule_code,
                        "Missing Confidentiality Tier",
                        f"Asset '{version.name}' does not have an assigned data confidentiality classification tier.",
                        cat_conf_rule.severity,
                        cat_conf_rule.default_sla_days,
                    ))

            # Check open issues in DB to avoid duplicate entries
            for r_code, rule_name, rule_desc, rule_sev, sla_days in violations:
                check_stmt = select(ComplianceIssue).where(
                    ComplianceIssue.target_asset_head_id == head.id,
                    or_(
                        ComplianceIssue.rule_code == r_code,
                        ComplianceIssue.title == rule_name,
                    ),
                    ComplianceIssue.status == IssueStatusEnum.OPEN,
                )
                check_res = await self.db.execute(check_stmt)
                existing = check_res.scalar_one_or_none()

                if existing:
                    existing_count += 1
                    created_or_found.append(existing)
                else:
                    new_count += 1
                    rule_deadline = now + timedelta(days=sla_days)
                    new_issue = ComplianceIssue(
                        id=uuid.uuid7(),
                        target_asset_head_id=head.id,
                        rule_code=r_code,
                        app_owner_id=actor,
                        assigned_steward_id=actor,
                        title=rule_name,
                        description=rule_desc,
                        severity=rule_sev,
                        status=IssueStatusEnum.OPEN,
                        remediation_deadline=rule_deadline,
                        created_by=actor,
                        created_at=now,
                    )
                    self.db.add(new_issue)
                    created_or_found.append(new_issue)

        await self.db.commit()

        # Re-query list to return formatted models
        issue_reads = [ComplianceIssueRead.model_validate(i) for i in created_or_found]

        return ComplianceScanResponse(
            scanned_assets_count=len(heads),
            issues_detected_count=len(created_or_found),
            new_issues_created_count=new_count,
            existing_issues_count=existing_count,
            issues=issue_reads,
        )

    async def remediate_issue(
        self,
        issue_id: uuid.UUID,
        resolved_by_user_id: Optional[uuid.UUID] = None,
        auto_fix_payload: Optional[Dict[str, Any]] = None,
    ) -> ComplianceIssue:
        """Resolve a compliance issue, applying automated remediations to asset payload."""
        issue = await self.get_issue(issue_id)
        if issue.status == IssueStatusEnum.RESOLVED:
            return issue

        now = datetime.now(timezone.utc)

        # 1. Apply auto-fix logic to asset draft/version if relevant
        head_stmt = (
            select(AssetHead)
            .options(
                selectinload(AssetHead.active_draft_version),
                selectinload(AssetHead.published_version),
            )
            .where(AssetHead.id == issue.target_asset_head_id)
        )
        head_res = await self.db.execute(head_stmt)
        head = head_res.scalar_one_or_none()

        if head:
            target_version = head.active_draft_version or head.published_version
            if target_version:
                attrs = dict(target_version.attributes_payload or {})

                if "PII" in issue.title:
                    attrs["PII"] = False
                    target_version.attributes_payload = attrs
                elif "Confidentiality" in issue.title:
                    attrs["CONFIDENTIALITY"] = "INTERNAL"
                    target_version.attributes_payload = attrs
                elif "Description" in issue.title:
                    existing = target_version.description_markdown or ""
                    if len(existing.strip()) < 50:
                        target_version.description_markdown = (
                            f"{existing.strip()} - Certified enterprise asset meeting governance compliance standards."
                        ).strip(" -")

        # 2. Mark issue RESOLVED
        issue.status = IssueStatusEnum.RESOLVED
        issue.resolved_at = now

        await self.db.commit()
        await self.db.refresh(issue)
        return issue
