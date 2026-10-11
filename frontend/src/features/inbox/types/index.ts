export type TaskDecision = "PENDING" | "APPROVED" | "REJECTED" | "CHANGES_REQUESTED";

export interface IWorkflowTask {
  id: string;
  workflow_instance_id: string;
  stage_id: string;
  assigned_role: string;
  assigned_user_id?: string | null;
  decision: TaskDecision;
  decision_notes?: string | null;
  decided_by?: string | null;
  decided_at?: string | null;
  due_at: string;
  created_at?: string | null;

  // Enriched context
  stage_name?: string | null;
  stage_order?: number | null;
  asset_version_id?: string | null;
  asset_head_id?: string | null;
  asset_name?: string | null;
  asset_domain_id?: string | null;
  asset_version_number?: number | null;
  proposer_name?: string | null;
  proposer_id?: string | null;
}

export type TaskDecisionAction = "APPROVED" | "REJECTED";

export interface ITaskActionPayload {
  taskId: string;
  decision: TaskDecisionAction;
  decisionNotes?: string;
}

export interface IWorkflowFilterOptions {
  status: "PENDING" | "APPROVED" | "REJECTED" | "ALL";
  role?: string;
}
