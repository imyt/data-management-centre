import { create } from "zustand";

export interface IRemediationUiState {
  selectedIssueId: string | null;
  severityFilter: string;
  statusFilter: string;
  lastScanMessage: string | null;
  setSelectedIssueId: (id: string | null) => void;
  setSeverityFilter: (severity: string) => void;
  setStatusFilter: (status: string) => void;
  setLastScanMessage: (message: string | null) => void;
  reset: () => void;
}

const INITIAL_STATE = {
  selectedIssueId: null,
  severityFilter: "ALL",
  statusFilter: "ALL",
  lastScanMessage: null,
} as const;

export const useRemediationUiStore = create<IRemediationUiState>()((set) => ({
  ...INITIAL_STATE,
  setSelectedIssueId: (id) => set({ selectedIssueId: id }),
  setSeverityFilter: (severity) => set({ severityFilter: severity }),
  setStatusFilter: (status) => set({ statusFilter: status }),
  setLastScanMessage: (message) => set({ lastScanMessage: message }),
  reset: () => set({ ...INITIAL_STATE }),
}));
