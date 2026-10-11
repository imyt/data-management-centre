import * as sdk from "@/api/generated/sdk.gen";
import type {
  WorkbenchSummary,
  WorkbenchIssue,
  StorageControlItem,
  PhysicalTableItem,
  PhysicalColumnItem,
  UsageEntitlementItem,
} from "../types";

export const workbenchApi = {
  async getSummary(appHeadId: string): Promise<WorkbenchSummary> {
    const res = await sdk.getWorkbenchSummaryApiV1WorkbenchAppHeadIdSummaryGet({
      path: { app_head_id: appHeadId },
      throwOnError: true,
    });
    return res.data as unknown as WorkbenchSummary;
  },

  async listIssues(
    appHeadId: string,
    filters?: { status?: string; severity?: string; rule_code?: string }
  ): Promise<WorkbenchIssue[]> {
    const res = await sdk.listWorkbenchIssuesApiV1WorkbenchAppHeadIdIssuesGet({
      path: { app_head_id: appHeadId },
      query: filters,
      throwOnError: true,
    });
    return (res.data || []) as unknown as WorkbenchIssue[];
  },

  async remediateIntegrity(body: {
    issue_id: string;
    integration_id: string;
    pattern: string;
    pattern_details: string;
    dataset_id?: string | null;
  }) {
    const res = await sdk.remediateIntegrityApiV1WorkbenchRemediateIntegrityPost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async remediateDrift(body: {
    issue_id: string;
    classifications: Array<{
      column_id: string;
      is_pii: boolean;
      masking_strategy: string;
      isr_classification: string;
      business_term_name?: string | null;
    }>;
  }) {
    const res = await sdk.remediateDriftApiV1WorkbenchRemediateDriftPost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async remediatePurge(body: {
    issue_id: string;
    storage_control_id: string;
    attestation_notes: string;
  }) {
    const res = await sdk.remediatePurgeApiV1WorkbenchRemediatePurgePost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async remediateMasking(body: {
    issue_id: string;
    column_id: string;
    masking_strategy: string;
  }) {
    const res = await sdk.remediateMaskingApiV1WorkbenchRemediateMaskingPost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async requestExemption(body: {
    issue_id: string;
    justification: string;
    compensating_controls: string;
    duration_days: number;
  }) {
    const res = await sdk.requestExemptionApiV1WorkbenchExemptionsRequestPost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async listStorageControls(appHeadId: string): Promise<StorageControlItem[]> {
    const res = await sdk.listAppStorageControlsApiV1StorageAppAppHeadIdGet({
      path: { app_head_id: appHeadId },
      throwOnError: true,
    });
    return (res.data || []) as unknown as StorageControlItem[];
  },

  async createStorageControl(body: {
    app_head_id: string;
    storage_name: string;
    storage_type: string;
    encryption_algorithm: string;
    kms_key_arn?: string | null;
    retention_period_days: number;
    purge_mechanism: string;
  }) {
    const res = await sdk.createStorageControlApiV1StoragePost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async toggleLegalHold(storageId: string, active: boolean, reason?: string | null) {
    const res = await sdk.toggleLegalHoldApiV1StorageStorageIdLegalHoldPost({
      path: { storage_id: storageId },
      body: { active, reason: reason || undefined },
      throwOnError: true,
    });
    return res.data;
  },

  async attestPurge(storageId: string, notes?: string | null) {
    const res = await sdk.attestPurgeApiV1StorageStorageIdAttestPurgePost({
      path: { storage_id: storageId },
      body: { notes: notes || undefined },
      throwOnError: true,
    });
    return res.data;
  },

  async listTables(appHeadId: string): Promise<PhysicalTableItem[]> {
    const res = await sdk.listTablesApiV1SchemaHarvestAppAppHeadIdTablesGet({
      path: { app_head_id: appHeadId },
      throwOnError: true,
    });
    return (res.data || []) as unknown as PhysicalTableItem[];
  },

  async listColumns(
    appHeadId: string,
    params?: { table_id?: string; drift_status?: string }
  ): Promise<PhysicalColumnItem[]> {
    const res = await sdk.listColumnsApiV1SchemaHarvestAppAppHeadIdColumnsGet({
      path: { app_head_id: appHeadId },
      query: params,
      throwOnError: true,
    });
    return (res.data || []) as unknown as PhysicalColumnItem[];
  },

  async triggerHarvest(appHeadId: string, storageControlId?: string | null) {
    const res = await sdk.triggerHarvestApiV1SchemaHarvestTriggerPost({
      body: {
        app_head_id: appHeadId,
        storage_control_id: storageControlId || undefined,
      },
      throwOnError: true,
    });
    return res.data;
  },

  async updateColumnClassification(
    columnId: string,
    data: {
      is_pii: boolean;
      masking_strategy: string;
      isr_classification: string;
      business_term_name?: string | null;
    }
  ) {
    const res = await sdk.updateColumnClassificationApiV1SchemaHarvestColumnsColumnIdClassificationPut({
      path: { column_id: columnId },
      body: data as any,
      throwOnError: true,
    });
    return res.data;
  },

  async listEntitlements(appHeadId: string): Promise<UsageEntitlementItem[]> {
    const res = await sdk.listAppEntitlementsApiV1PrivacyAppAppHeadIdEntitlementsGet({
      path: { app_head_id: appHeadId },
      throwOnError: true,
    });
    return (res.data || []) as unknown as UsageEntitlementItem[];
  },

  async createEntitlement(body: {
    app_head_id: string;
    consumer_app_head_id: string;
    authorized_purpose: string;
    allowed_geo_regions: string[];
    duration_days: number;
  }) {
    const res = await sdk.createEntitlementApiV1PrivacyEntitlementsPost({
      body: body as any,
      throwOnError: true,
    });
    return res.data;
  },

  async revokeEntitlement(entitlementId: string) {
    const res = await sdk.revokeEntitlementApiV1PrivacyEntitlementsEntitlementIdRevokePost({
      path: { entitlement_id: entitlementId },
      throwOnError: true,
    });
    return res.data;
  },
};
