import type {
  IComplianceIssue,
  IComplianceScanResponse,
  IRemediateIssueRequest,
} from "../types";

const getBaseUrl = (): string => {
  return "http://localhost:8000";
};

const getHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = localStorage.getItem("dgc_auth_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

export const complianceApi = {
  async getIssues(params?: {
    status?: string;
    severity?: string;
    asset_id?: string;
  }): Promise<IComplianceIssue[]> {
    const url = new URL(`${getBaseUrl()}/api/v1/compliance/issues`);
    if (params?.status && params.status !== "ALL") {
      url.searchParams.set("status", params.status);
    }
    if (params?.severity && params.severity !== "ALL") {
      url.searchParams.set("severity", params.severity);
    }
    if (params?.asset_id) {
      url.searchParams.set("asset_id", params.asset_id);
    }

    const res = await fetch(url.toString(), {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch compliance issues: ${res.statusText}`);
    }
    return res.json();
  },

  async runScan(domainId?: string): Promise<IComplianceScanResponse> {
    const url = `${getBaseUrl()}/api/v1/compliance/scan`;
    const res = await fetch(url, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(domainId ? { domain_id: domainId } : {}),
    });
    if (!res.ok) {
      throw new Error(`Failed to execute compliance scan: ${res.statusText}`);
    }
    return res.json();
  },

  async remediateIssue(
    issueId: string,
    payload?: IRemediateIssueRequest
  ): Promise<IComplianceIssue> {
    const url = `${getBaseUrl()}/api/v1/compliance/issues/${issueId}/remediate`;
    const res = await fetch(url, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(payload || { auto_apply_fix: true }),
    });
    if (!res.ok) {
      throw new Error(`Failed to remediate compliance issue: ${res.statusText}`);
    }
    return res.json();
  },
};
