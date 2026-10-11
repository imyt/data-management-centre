/**
 * Public contract for Remediation feature module.
 * Other modules and routing layers MUST only import through this barrel.
 */

// Pages
export { RemediationPage } from "./pages/remediation-page";

// Components
export { RemediationHub } from "./components/RemediationHub";

// UI Store
export { useRemediationUiStore } from "./stores/remediation.store";
export type { IRemediationUiState } from "./stores/remediation.store";

// Types
export type {
  IssueSeverity,
  IssueStatus,
  IComplianceIssue,
  IComplianceScanResponse,
  IRemediateIssueRequest,
  IRemediationHubProps,
} from "./types";

// API
export { complianceApi } from "./api/compliance.api";
