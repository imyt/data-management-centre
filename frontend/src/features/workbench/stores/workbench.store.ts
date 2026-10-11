import { create } from "zustand";
import type { WorkbenchIssue } from "../types";

export type WorkbenchTab = "inbox" | "movement" | "storage" | "privacy" | "harvest";
export type UrgencyFilter = "ALL" | "CRITICAL" | "HIGH" | "BREACHING_SOON" | "WAIVERS";
export type RemediationModalType = "INTEGRITY" | "DRIFT" | "PURGE" | "MASKING" | "EXEMPTION";

interface WorkbenchUiState {
  selectedAppHeadId: string | null;
  activeTab: WorkbenchTab;
  urgencyFilter: UrgencyFilter;
  activeIssue: WorkbenchIssue | null;
  remediationModalType: RemediationModalType | null;
  isCreateStorageModalOpen: boolean;
  isCreateEntitlementModalOpen: boolean;

  setSelectedAppHeadId: (id: string) => void;
  setActiveTab: (tab: WorkbenchTab) => void;
  setUrgencyFilter: (filter: UrgencyFilter) => void;
  openRemediationModal: (issue: WorkbenchIssue, type: RemediationModalType) => void;
  closeRemediationModal: () => void;
  setCreateStorageModalOpen: (open: boolean) => void;
  setCreateEntitlementModalOpen: (open: boolean) => void;
}

export const useWorkbenchUiStore = create<WorkbenchUiState>((set) => ({
  selectedAppHeadId: null,
  activeTab: "inbox",
  urgencyFilter: "ALL",
  activeIssue: null,
  remediationModalType: null,
  isCreateStorageModalOpen: false,
  isCreateEntitlementModalOpen: false,

  setSelectedAppHeadId: (id) => set({ selectedAppHeadId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setUrgencyFilter: (filter) => set({ urgencyFilter: filter }),
  openRemediationModal: (issue, type) => set({ activeIssue: issue, remediationModalType: type }),
  closeRemediationModal: () => set({ activeIssue: null, remediationModalType: null }),
  setCreateStorageModalOpen: (open) => set({ isCreateStorageModalOpen: open }),
  setCreateEntitlementModalOpen: (open) => set({ isCreateEntitlementModalOpen: open }),
}));
