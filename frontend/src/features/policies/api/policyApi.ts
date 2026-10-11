import "@/api/client";
import * as sdk from "@/api/generated/sdk.gen";
import type { UpdatePolicyRuleApiV1PoliciesRulesRuleIdPutData, CreateCustomPolicyRuleApiV1PoliciesRulesPostData } from "@/api/generated/types.gen";

export interface PolicyRuleItem {
  id: string;
  rule_code: string;
  name: string;
  description: string;
  category: "DATA_MOVEMENT" | "STORAGE_RETENTION" | "PRIVACY_USAGE" | "SCHEMA_DRIFT" | "CATALOG_METADATA";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  enforcement_mode: "BLOCKING" | "ADVISORY" | "DISABLED";
  is_enabled: boolean;
  default_sla_days: number;
  target_entity_type: string;
  parameters: Record<string, unknown>;
  remediation_guidance?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyRulesResponse {
  summary: {
    total_rules: number;
    enabled_rules: number;
    disabled_rules: number;
    blocking_rules: number;
    advisory_rules: number;
    by_category: Record<string, number>;
  };
  rules: PolicyRuleItem[];
}

export interface UpdatePolicyRulePayload {
  name?: string;
  description?: string;
  enforcement_mode?: "BLOCKING" | "ADVISORY" | "DISABLED";
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  default_sla_days?: number;
  is_enabled?: boolean;
  parameters?: Record<string, unknown>;
  remediation_guidance?: string;
}

export interface CreateCustomRulePayload {
  rule_code: string;
  name: string;
  description: string;
  category: "DATA_MOVEMENT" | "STORAGE_RETENTION" | "PRIVACY_USAGE" | "SCHEMA_DRIFT" | "CATALOG_METADATA";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  enforcement_mode: "BLOCKING" | "ADVISORY" | "DISABLED";
  default_sla_days: number;
  target_entity_type?: string;
  parameters?: Record<string, unknown>;
  remediation_guidance?: string;
}

export const policyApi = {
  listRules: async (category?: string, enforcementMode?: string, enabledOnly?: boolean): Promise<PolicyRulesResponse> => {
    const res = await sdk.listPolicyRulesApiV1PoliciesRulesGet({
      query: {
        category: category && category !== "ALL" ? category : undefined,
        enforcement_mode: enforcementMode && enforcementMode !== "ALL" ? enforcementMode : undefined,
        enabled_only: enabledOnly ? true : undefined,
      },
      throwOnError: true,
    });
    return res.data as unknown as PolicyRulesResponse;
  },

  getRule: async (ruleId: string): Promise<PolicyRuleItem> => {
    const res = await sdk.getPolicyRuleApiV1PoliciesRulesRuleIdGet({
      path: { rule_id: ruleId },
      throwOnError: true,
    });
    return res.data as unknown as PolicyRuleItem;
  },

  updateRule: async (ruleId: string, payload: UpdatePolicyRulePayload): Promise<PolicyRuleItem> => {
    const res = await sdk.updatePolicyRuleApiV1PoliciesRulesRuleIdPut({
      path: { rule_id: ruleId },
      body: payload as UpdatePolicyRuleApiV1PoliciesRulesRuleIdPutData["body"],
      throwOnError: true,
    });
    return res.data as unknown as PolicyRuleItem;
  },

  toggleRule: async (ruleId: string, isEnabled: boolean): Promise<{ id: string; rule_code: string; is_enabled: boolean; enforcement_mode: string }> => {
    const res = await sdk.togglePolicyRuleApiV1PoliciesRulesRuleIdTogglePatch({
      path: { rule_id: ruleId },
      body: { is_enabled: isEnabled },
      throwOnError: true,
    });
    return res.data as unknown as { id: string; rule_code: string; is_enabled: boolean; enforcement_mode: string };
  },

  createCustomRule: async (payload: CreateCustomRulePayload): Promise<PolicyRuleItem> => {
    const res = await sdk.createCustomPolicyRuleApiV1PoliciesRulesPost({
      body: payload as CreateCustomPolicyRuleApiV1PoliciesRulesPostData["body"],
      throwOnError: true,
    });
    return res.data as unknown as PolicyRuleItem;
  },

  resetDefaults: async (): Promise<{ status: string; message: string }> => {
    const res = await sdk.resetPolicyRulesToDefaultsApiV1PoliciesRulesResetDefaultsPost({
      throwOnError: true,
    });
    return res.data as unknown as { status: string; message: string };
  },

  evaluatePolicies: async (domainId?: string): Promise<{ status: string; new_issues_count: number; existing_issues_count: number; total_issues_identified: number }> => {
    const res = await sdk.evaluatePolicyRulesApiV1PoliciesEvaluatePost({
      query: domainId ? { domain_id: domainId } : undefined,
      throwOnError: true,
    });
    return res.data as unknown as { status: string; new_issues_count: number; existing_issues_count: number; total_issues_identified: number };
  },
};
