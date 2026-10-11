import * as sdk from "@/api/generated/sdk.gen";

export interface PendingIntegrationItem {
  id: string;
  itsm_integration_id: string;
  app_head_id: string;
  app_name: string;
  app_ci: string;
  partner_app_name: string;
  direction: string;
  transfer_type: string;
  frequency: string;
  integrity_pattern: string;
  integrity_pattern_details: string | null;
  governance_status: string;
  bound_datasets: Array<{ id: string; name: string; isr_classification: string }>;
  bound_datasets_count: number;
  submitted_at: string;
}

export interface PendingWaiverItem {
  id: string;
  issue_id: string | null;
  rule_code: string;
  issue_title: string;
  severity: string;
  app_name: string;
  app_ci: string;
  justification: string;
  compensating_controls: string;
  status: string;
  expires_at: string;
  requested_by_name: string;
  requested_at: string;
}

export interface VerificationsResponse {
  summary: {
    total_pending: number;
    pending_integrations: number;
    pending_waivers: number;
  };
  integrations: PendingIntegrationItem[];
  waivers: PendingWaiverItem[];
}

export const verificationApi = {
  async listPendingVerifications(): Promise<VerificationsResponse> {
    const res = await sdk.listPendingVerificationsApiV1VerificationsGet({
      throwOnError: true,
    });
    return res.data as unknown as VerificationsResponse;
  },

  async reviewIntegration(integrationId: string, approved: boolean, notes: string) {
    const res = await sdk.reviewIntegrationApiV1VerificationsIntegrationsIntegrationIdReviewPost({
      path: { integration_id: integrationId },
      body: { approved, decision_notes: notes },
      throwOnError: true,
    });
    return res.data;
  },

  async reviewExemption(exemptionId: string, approved: boolean, notes: string) {
    const res = await sdk.reviewExemptionApiV1VerificationsExemptionsExemptionIdReviewPost({
      path: { exemption_id: exemptionId },
      body: { approved, decision_notes: notes },
      throwOnError: true,
    });
    return res.data;
  },
};
