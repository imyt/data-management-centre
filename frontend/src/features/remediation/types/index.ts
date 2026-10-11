export type IssueSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IssueStatus =
  | "OPEN"
  | "IN_REMEDIATION"
  | "PENDING_VERIFICATION"
  | "RESOLVED"
  | "EXCEPTION_GRANTED";

export interface IComplianceIssue {
  id: string;
  target_asset_head_id: string;
  app_owner_id: string;
  assigned_steward_id?: string | null;
  title: string;
  description: string;
  severity: IssueSeverity;
  status: IssueStatus;
  remediation_deadline: string;
  created_by: string;
  created_at: string;
  resolved_at?: string | null;
  asset_name?: string | null;
}

export interface IComplianceScanResponse {
  scanned_assets_count: number;
  issues_detected_count: number;
  new_issues_created_count: number;
  existing_issues_count: number;
  issues: IComplianceIssue[];
}

export interface IRemediateIssueRequest {
  resolution_notes?: string;
  auto_apply_fix?: boolean;
}

export interface IRemediationHubProps {
  initialSeverityFilter?: string;
}
