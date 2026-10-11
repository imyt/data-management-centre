"""Pydantic v2 DTOs for Application-Level Data Movement & Integrity Controls."""
import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.data_movement import (
    IntegrationDirectionEnum,
    TransferTypeEnum,
    TransferFrequencyEnum,
    IntegrityPatternEnum,
    ISRClassificationEnum,
    IntegrationGovernanceStatusEnum,
)


# ============================================================================
# DATASET SCHEMAS
# ============================================================================

class DataSetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Unique dataset name scoped to application")
    description: Optional[str] = Field(None, description="Detailed dataset markdown description")
    business_context: str = Field(..., min_length=10, description="Business context and intended purpose")
    isr_classification: ISRClassificationEnum = Field(
        default=ISRClassificationEnum.INTERNAL,
        description="Information Security Risk data classification level"
    )
    data_categories: List[str] = Field(
        default_factory=list,
        description="Data domain categories (e.g. ['CUSTOMER_PII', 'FINANCIAL', 'TRANSACTION'])"
    )


class DataSetCreate(DataSetBase):
    pass


class DataSetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    business_context: Optional[str] = Field(None, min_length=10)
    isr_classification: Optional[ISRClassificationEnum] = None
    data_categories: Optional[List[str]] = None


class DataSetUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    integration_id: uuid.UUID
    itsm_integration_id: str
    direction: IntegrationDirectionEnum
    partner_app_head_id: uuid.UUID
    partner_application_name: str
    transfer_type: TransferTypeEnum
    frequency: TransferFrequencyEnum
    governance_status: IntegrationGovernanceStatusEnum


class DataSetRead(DataSetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_head_id: uuid.UUID
    app_head_id: uuid.UUID
    is_archived: bool
    archived_at: Optional[datetime] = None
    created_by: uuid.UUID
    updated_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0


class DataSetDeleteBlockedResponse(BaseModel):
    detail: str
    dataset_id: uuid.UUID
    dataset_name: str
    blocking_integrations: List[DataSetUsageRead]


# ============================================================================
# DATA MOVEMENT SCOPE SCHEMAS
# ============================================================================

class DataMovementScopeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    data_set_id: uuid.UUID
    dataset_name: Optional[str] = None
    isr_classification: Optional[ISRClassificationEnum] = None
    data_categories: List[str] = Field(default_factory=list)
    retention_period_days: Optional[int] = None
    encryption_in_transit: bool = True
    created_at: datetime


class BindScopeRequest(BaseModel):
    data_set_id: uuid.UUID
    retention_period_days: Optional[int] = Field(None, ge=1, le=3650)
    encryption_in_transit: bool = True


# ============================================================================
# APPLICATION INTEGRATION SCHEMAS
# ============================================================================

class ApplicationIntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_head_id: uuid.UUID
    itsm_integration_id: str
    source_app_head_id: uuid.UUID
    source_app_name: Optional[str] = None
    target_app_head_id: uuid.UUID
    target_app_name: Optional[str] = None
    direction: IntegrationDirectionEnum
    transfer_type: TransferTypeEnum
    frequency: TransferFrequencyEnum
    itsm_last_synced_at: datetime
    is_active_in_itsm: bool
    governance_status: IntegrationGovernanceStatusEnum
    integrity_pattern: IntegrityPatternEnum
    integrity_pattern_details: Optional[str] = None
    governance_certified_at: Optional[datetime] = None
    certified_by: Optional[uuid.UUID] = None
    certified_by_name: Optional[str] = None
    created_at: datetime
    bound_datasets: List[DataMovementScopeRead] = Field(default_factory=list)
    sla_days_remaining: Optional[int] = None
    sla_breached: bool = False


class SetIntegrityPatternRequest(BaseModel):
    integrity_pattern: IntegrityPatternEnum
    integrity_pattern_details: Optional[str] = Field(
        None,
        description="Technical validation details or tooling implementation (e.g. SHA-256 header hash verification)"
    )


class SubmitCertificationRequest(BaseModel):
    certification_notes: Optional[str] = Field(
        None,
        description="Attestation comments for Data Steward verification"
    )


class VerifyCertificationRequest(BaseModel):
    approved: bool
    decision_notes: Optional[str] = Field(
        None,
        description="Steward approval rationale or requested corrections"
    )


# ============================================================================
# APPLICATION PROFILE SCHEMAS
# ============================================================================

class ApplicationProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_head_id: uuid.UUID
    itsm_system_id: str
    itsm_system_name: str
    cmdb_criticality: str
    app_owner_id: uuid.UUID
    app_owner_name: Optional[str] = None
    synced_at: datetime
    datasets_count: int = 0
    integrations_count: int = 0
