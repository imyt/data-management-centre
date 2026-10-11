// Type-safe API Client powered by @hey-api/openapi-ts SDK
import { client } from "./generated/client.gen";
import * as sdk from "./generated/sdk.gen";
import type {
  AssetHeadRead,
  AssetVersionRead,
  AssetTypeRead,
  AssetTypeAttributeAssignmentRead,
  AttributeTypeRead,
  CommunityRead,
  DomainRead,
  DiffResponse,
  UserRead,
  AssetCreate,
  AssetDraftUpdate,
} from "./generated/types.gen";

// Export Hey-API Generated Models with clean aliases
export type AssetHead = AssetHeadRead;
export type AssetVersion = AssetVersionRead;
export type AssetType = AssetTypeRead;
export type AssetTypeAttributeAssignment = AssetTypeAttributeAssignmentRead;
export type AttributeType = AttributeTypeRead;
export type Community = CommunityRead;
export type Domain = DomainRead;
export type User = UserRead;
export type {
  DiffResponse,
  AssetCreate,
  AssetDraftUpdate,
  AssetTypeAttributeAssignmentRead,
  AttributeTypeRead,
};
export type {
  ApplicationProfileRead,
  DataSetRead,
  DataSetCreate,
  DataSetUpdate,
  DataSetUsageRead,
  ApplicationIntegrationRead,
  DataMovementScopeRead,
  BindScopeRequest,
  SetIntegrityPatternRequest,
  SubmitCertificationRequest,
  VerifyCertificationRequest,
  IsrClassificationEnum,
  IntegrationGovernanceStatusEnum,
  IntegrationDirectionEnum,
  TransferTypeEnum,
  TransferFrequencyEnum,
  IntegrityPatternEnum,
} from "./generated/types.gen";

// Clean aliased Query Options and Mutations for Data Movement
export {
  listApplicationsApiV1ApplicationsGetOptions as listApplicationsOptions,
  getApplicationApiV1ApplicationsAppHeadIdGetOptions as getApplicationOptions,
  listApplicationDatasetsApiV1ApplicationsAppHeadIdDatasetsGetOptions as listApplicationDatasetsOptions,
  getDatasetApiV1ApplicationsAppHeadIdDatasetsDatasetIdGetOptions as getDatasetOptions,
  getDatasetUsagesApiV1ApplicationsAppHeadIdDatasetsDatasetIdUsagesGetOptions as getDatasetUsagesOptions,
  createDatasetApiV1ApplicationsAppHeadIdDatasetsPostMutation as createDatasetMutation,
  updateDatasetApiV1ApplicationsAppHeadIdDatasetsDatasetIdPutMutation as updateDatasetMutation,
  deleteDatasetApiV1ApplicationsAppHeadIdDatasetsDatasetIdDeleteMutation as deleteDatasetMutation,
  listApplicationIntegrationsApiV1ApplicationsAppHeadIdIntegrationsGetOptions as listApplicationIntegrationsOptions,
  getIntegrationApiV1IntegrationsIntegrationIdGetOptions as getIntegrationOptions,
  bindScopeApiV1IntegrationsIntegrationIdBindScopePostMutation as bindScopeMutation,
  unbindScopeApiV1IntegrationsIntegrationIdUnbindScopeDatasetIdDeleteMutation as unbindScopeMutation,
  setIntegrityPatternApiV1IntegrationsIntegrationIdIntegrityPatternPutMutation as setIntegrityPatternMutation,
  submitCertificationApiV1IntegrationsIntegrationIdSubmitCertificationPostMutation as submitCertificationMutation,
  verifyCertificationApiV1IntegrationsIntegrationIdVerifyCertificationPostMutation as verifyCertificationMutation,
} from "./generated/@tanstack/react-query.gen";
export * from "./generated/@tanstack/react-query.gen";

export interface StageApprovalTask {
  id: string;
  workflow_instance_id: string;
  stage_id: string;
  assigned_role: string;
  assigned_user_id?: string | null;
  decision: "PENDING" | "APPROVED" | "REJECTED" | "CHANGES_REQUESTED";
  decision_notes?: string | null;
  decided_by?: string | null;
  decided_at?: string | null;
  due_at: string;
  created_at?: string | null;
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

// Configure base URL and request auth interceptor
client.setConfig({
  baseUrl: "http://localhost:8000",
});

client.interceptors.request.use((request) => {
  const token = localStorage.getItem("dgc_auth_token");
  if (token) {
    request.headers.set("Authorization", `Bearer ${token}`);
  }
  return request;
});

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string; user?: User }> {
    const res = await sdk.loginApiV1AuthLoginPost({
      body: { email, password },
      throwOnError: true,
    });
    if (!res.data?.access_token) {
      throw new Error("No token returned");
    }
    localStorage.setItem("dgc_auth_token", res.data.access_token);
    return {
      access_token: res.data.access_token,
      user: res.data.user as User,
    };
  },

  async getMe(): Promise<User> {
    const res = await sdk.getMeApiV1AuthMeGet({ throwOnError: true });
    return res.data as User;
  },

  logout() {
    localStorage.removeItem("dgc_auth_token");
  },

  // Metamodel
  async getAssetTypes(): Promise<AssetType[]> {
    const res = await sdk.listAssetTypesApiV1MetamodelAssetTypesGet({ throwOnError: true });
    return (res.data || []) as AssetType[];
  },

  // Organization
  async getCommunities(): Promise<Community[]> {
    const res = await sdk.listCommunitiesApiV1CommunitiesGet({ throwOnError: true });
    return (res.data || []) as Community[];
  },

  async getDomains(communityId?: string): Promise<Domain[]> {
    const res = await sdk.listDomainsApiV1DomainsGet({
      query: communityId ? { community_id: communityId } : undefined,
      throwOnError: true,
    });
    return (res.data || []) as Domain[];
  },

  // Assets
  async getAssets(params?: {
    domain_id?: string;
    asset_type_id?: string;
    search?: string;
  }): Promise<AssetHead[]> {
    const res = await sdk.listAssetsApiV1AssetsGet({
      query: {
        domain_id: params?.domain_id,
        asset_type_id: params?.asset_type_id,
        search: params?.search,
      },
      throwOnError: true,
    });
    return (res.data || []) as AssetHead[];
  },

  async getAsset(assetHeadId: string): Promise<AssetHead> {
    const res = await sdk.getAssetApiV1AssetsAssetHeadIdGet({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return res.data as AssetHead;
  },

  async createAsset(data: {
    domain_id: string;
    asset_type_id: string;
    name: string;
    description_markdown?: string;
    attributes_payload?: Record<string, unknown>;
  }): Promise<AssetHead> {
    const res = await sdk.createAssetHeadAndInitialDraftApiV1AssetsPost({
      body: data,
      throwOnError: true,
    });
    return res.data as AssetHead;
  },

  async acquireDraft(assetHeadId: string): Promise<AssetVersion> {
    const res = await sdk.acquireOrForkDraftApiV1AssetsAssetHeadIdDraftPost({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return res.data as AssetVersion;
  },

  async updateDraft(
    assetHeadId: string,
    data: {
      name?: string;
      description_markdown?: string;
      attributes_payload?: Record<string, unknown>;
    }
  ): Promise<AssetVersion> {
    const res = await sdk.updateDraftApiV1AssetsAssetHeadIdDraftPut({
      path: { asset_head_id: assetHeadId },
      body: data,
      throwOnError: true,
    });
    return res.data as AssetVersion;
  },

  async releaseDraftLock(assetHeadId: string): Promise<{ status: string }> {
    const res = await sdk.releaseLockApiV1AssetsAssetHeadIdDraftReleaseLockPost({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return (res.data || { status: "released" }) as { status: string };
  },

  async releaseLock(assetHeadId: string): Promise<{ status: string }> {
    return this.releaseDraftLock(assetHeadId);
  },

  async publishDraft(assetHeadId: string): Promise<AssetVersion> {
    const res = await sdk.publishAssetVersionApiV1AssetsAssetHeadIdPublishPost({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return res.data as AssetVersion;
  },

  async publishAsset(assetHeadId: string): Promise<AssetVersion> {
    return this.publishDraft(assetHeadId);
  },

  async getDiff(assetHeadId: string): Promise<DiffResponse> {
    const res = await sdk.getVisualDiffApiV1AssetsAssetHeadIdDiffGet({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return res.data as DiffResponse;
  },

  async getHistory(assetHeadId: string): Promise<AssetVersion[]> {
    const res = await sdk.getVersionHistoryApiV1AssetsAssetHeadIdHistoryGet({
      path: { asset_head_id: assetHeadId },
      throwOnError: true,
    });
    return (res.data || []) as AssetVersion[];
  },

  async getVersionHistory(assetHeadId: string): Promise<AssetVersion[]> {
    return this.getHistory(assetHeadId);
  },

  // Governance Workflows
  async getWorkflowTasks(params?: {
    role?: string;
    status?: string;
  }): Promise<StageApprovalTask[]> {
    const res = await client.get<StageApprovalTask[]>({
      url: "/api/v1/workflows/tasks",
      query: {
        role: params?.role,
        status: params?.status,
      },
    });
    if (res.error) {
      throw new Error("Failed to fetch workflow tasks");
    }
    return (res.data || []) as StageApprovalTask[];
  },

  async actionWorkflowTask(
    taskId: string,
    data: { decision: "APPROVED" | "REJECTED"; decision_notes?: string }
  ): Promise<StageApprovalTask> {
    const res = await client.post<StageApprovalTask>({
      url: `/api/v1/workflows/tasks/${taskId}/action`,
      body: data,
      headers: {
        "Content-Type": "application/json",
      },
    });
    if (res.error) {
      throw new Error("Failed to action workflow task");
    }
    return res.data as StageApprovalTask;
  },
};


