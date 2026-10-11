export interface WorkbenchApplication {
  id: string | null;
  asset_head_id: string;
  itsm_system_id: string;
  itsm_system_name: string;
  cmdb_criticality: string;
  app_owner_name: string;
  app_owner_email: string;
  synced_at: string | null;
}

export interface WorkbenchPosture {
  health_score: number;
  total_defects: number;
  open_defects: number;
  resolved_defects: number;
  active_exemptions: number;
  breached_defects: number;
  breaching_soon_defects: number;
}

export interface ControlPlanesStats {
  data_movement: {
    total_integrations: number;
    compliant: number;
    ungoverned: number;
  };
  storage_retention: {
    total_repositories: number;
    legal_holds_active: number;
  };
  schema_harvest: {
    total_columns: number;
    unclassified_drift: number;
  };
  privacy_usage: {
    pii_columns: number;
    masked_columns: number;
    active_entitlements: number;
  };
}

export interface UrgentDefect {
  id: string;
  title: string;
  rule_code: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "OPEN" | "IN_REMEDIATION" | "RESOLVED" | "EXCEPTION_GRANTED";
  deadline: string;
  seconds_remaining: number;
  is_breached: boolean;
  is_breaching_soon: boolean;
  integration_id?: string | null;
  integration_name?: string | null;
  storage_control_id?: string | null;
  storage_name?: string | null;
  column_id?: string | null;
  column_name?: string | null;
}

export interface WorkbenchSummary {
  application: WorkbenchApplication;
  posture: WorkbenchPosture;
  control_planes: ControlPlanesStats;
  urgent_defects: UrgentDefect[];
}

export interface WorkbenchIssue {
  id: string;
  title: string;
  description: string;
  rule_code: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "OPEN" | "IN_REMEDIATION" | "RESOLVED" | "EXCEPTION_GRANTED";
  remediation_deadline: string;
  seconds_remaining: number;
  is_breached: boolean;
  created_at: string;
  resolved_at?: string | null;
  integration?: {
    id: string;
    itsm_integration_id: string;
    direction: string;
    transfer_type: string;
    governance_status: string;
    integrity_pattern: string;
  } | null;
  storage_control?: {
    id: string;
    storage_name: string;
    storage_type: string;
    retention_period_days: number;
    last_purge_attestation_at?: string | null;
    legal_hold_active: boolean;
  } | null;
  physical_column?: {
    id: string;
    table_name?: string | null;
    column_name: string;
    data_type: string;
    drift_status: string;
    is_pii: boolean;
    masking_strategy: string;
    isr_classification: string;
  } | null;
  exemption?: {
    id?: string | null;
    status?: string | null;
    justification?: string | null;
    compensating_controls?: string | null;
    expires_at?: string | null;
  } | null;
}

export interface StorageControlItem {
  id: string;
  app_head_id: string;
  storage_name: string;
  storage_type: string;
  encryption_algorithm: string;
  kms_key_arn?: string | null;
  retention_period_days: number;
  purge_mechanism: string;
  legal_hold_active: boolean;
  legal_hold_reason?: string | null;
  last_purge_attestation_at?: string | null;
  days_since_purge?: number | null;
  is_purge_overdue: boolean;
  attested_by_name?: string | null;
  created_at: string;
}

export interface PhysicalTableItem {
  id: string;
  app_head_id: string;
  storage_control_id?: string | null;
  storage_name: string;
  schema_name: string;
  table_name: string;
  row_count_estimate: number;
  total_columns: number;
  unclassified_drift_count: number;
  pii_count: number;
  is_active: boolean;
  created_at: string;
}

export interface PhysicalColumnItem {
  id: string;
  table_id: string;
  table_name: string;
  schema_name: string;
  column_name: string;
  data_type: string;
  is_nullable: boolean;
  drift_status: "SYNCED" | "ADDED_UNCLASSIFIED" | "DROPPED" | "TYPE_MODIFIED";
  is_pii: boolean;
  masking_strategy: "NONE" | "FULL_REDACTION" | "PARTIAL_MASK" | "TOKENIZE" | "HASH_SHA256";
  isr_classification: "PUBLIC" | "INTERNAL" | "RESTRICTED" | "HIGHLY_RESTRICTED";
  business_term_name?: string | null;
  linked_datasets_count: number;
  updated_at: string;
}

export interface UsageEntitlementItem {
  id: string;
  app_head_id: string;
  consumer_app_head_id: string;
  consumer_app_name: string;
  consumer_system_id: string;
  authorized_purpose: string;
  allowed_geo_regions: string[];
  is_active: boolean;
  is_expired: boolean;
  expires_at: string;
  approved_by_name: string;
  created_at: string;
}
