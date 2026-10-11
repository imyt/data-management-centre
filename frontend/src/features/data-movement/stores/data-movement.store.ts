import { create } from "zustand";

interface DataMovementUiState {
  selectedAppHeadId: string | null;
  activeTab: "integrations" | "datasets" | "compliance";
  searchQuery: string;
  isCreateDatasetOpen: boolean;
  editingDatasetId: string | null;
  deletingDatasetId: string | null;
  bindingIntegrationId: string | null;
  declaringPatternIntegrationId: string | null;
  verifyingIntegrationId: string | null;

  // High-density scaling controls for hundreds of integrations
  integrationStatusFilter: string;
  integrationDirectionFilter: string;
  integrationTransferTypeFilter: string;
  integrationViewMode: "compact" | "card";
  integrationPage: number;
  integrationPageSize: number;
  expandedIntegrationIds: string[];

  setSelectedAppHeadId: (id: string | null) => void;
  setActiveTab: (tab: "integrations" | "datasets" | "compliance") => void;
  setSearchQuery: (query: string) => void;
  setCreateDatasetOpen: (open: boolean) => void;
  setEditingDatasetId: (id: string | null) => void;
  setDeletingDatasetId: (id: string | null) => void;
  setBindingIntegrationId: (id: string | null) => void;
  setDeclaringPatternIntegrationId: (id: string | null) => void;
  setVerifyingIntegrationId: (id: string | null) => void;

  setIntegrationStatusFilter: (status: string) => void;
  setIntegrationDirectionFilter: (direction: string) => void;
  setIntegrationTransferTypeFilter: (transferType: string) => void;
  setIntegrationViewMode: (mode: "compact" | "card") => void;
  setIntegrationPage: (page: number) => void;
  setIntegrationPageSize: (size: number) => void;
  toggleExpandIntegration: (id: string) => void;
  expandAllIntegrations: (ids: string[]) => void;
  collapseAllIntegrations: () => void;
}

export const useDataMovementUiStore = create<DataMovementUiState>((set) => ({
  selectedAppHeadId: null,
  activeTab: "integrations",
  searchQuery: "",
  isCreateDatasetOpen: false,
  editingDatasetId: null,
  deletingDatasetId: null,
  bindingIntegrationId: null,
  declaringPatternIntegrationId: null,
  verifyingIntegrationId: null,

  integrationStatusFilter: "ALL",
  integrationDirectionFilter: "ALL",
  integrationTransferTypeFilter: "ALL",
  integrationViewMode: "compact",
  integrationPage: 1,
  integrationPageSize: 10,
  expandedIntegrationIds: [],

  setSelectedAppHeadId: (id) => set({ selectedAppHeadId: id, integrationPage: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSearchQuery: (query) => set({ searchQuery: query, integrationPage: 1 }),
  setCreateDatasetOpen: (open) => set({ isCreateDatasetOpen: open }),
  setEditingDatasetId: (id) => set({ editingDatasetId: id }),
  setDeletingDatasetId: (id) => set({ deletingDatasetId: id }),
  setBindingIntegrationId: (id) => set({ bindingIntegrationId: id }),
  setDeclaringPatternIntegrationId: (id) => set({ declaringPatternIntegrationId: id }),
  setVerifyingIntegrationId: (id) => set({ verifyingIntegrationId: id }),

  setIntegrationStatusFilter: (status) => set({ integrationStatusFilter: status, integrationPage: 1 }),
  setIntegrationDirectionFilter: (direction) => set({ integrationDirectionFilter: direction, integrationPage: 1 }),
  setIntegrationTransferTypeFilter: (transferType) => set({ integrationTransferTypeFilter: transferType, integrationPage: 1 }),
  setIntegrationViewMode: (mode) => set({ integrationViewMode: mode }),
  setIntegrationPage: (page) => set({ integrationPage: page }),
  setIntegrationPageSize: (size) => set({ integrationPageSize: size, integrationPage: 1 }),
  toggleExpandIntegration: (id) =>
    set((state) => ({
      expandedIntegrationIds: state.expandedIntegrationIds.includes(id)
        ? state.expandedIntegrationIds.filter((x) => x !== id)
        : [...state.expandedIntegrationIds, id],
    })),
  expandAllIntegrations: (ids) => set({ expandedIntegrationIds: ids }),
  collapseAllIntegrations: () => set({ expandedIntegrationIds: [] }),
}));
