import { create } from "zustand";

export interface IInboxUiState {
  filter: "PENDING" | "APPROVED" | "ALL";
  scope: "MY_ROLE" | "ALL_ROLES";
  selectedTaskId: string | null;
  activeActionModal: {
    isOpen: boolean;
    taskId: string | null;
    decision: "APPROVED" | "REJECTED" | null;
    assetName?: string;
  };
  setFilter: (filter: "PENDING" | "APPROVED" | "ALL") => void;
  setScope: (scope: "MY_ROLE" | "ALL_ROLES") => void;
  setSelectedTaskId: (id: string | null) => void;
  openActionModal: (taskId: string, decision: "APPROVED" | "REJECTED", assetName?: string) => void;
  closeActionModal: () => void;
  reset: () => void;
}

const INITIAL_STATE = {
  filter: "PENDING" as const,
  scope: "MY_ROLE" as const,
  selectedTaskId: null,
  activeActionModal: {
    isOpen: false,
    taskId: null,
    decision: null,
    assetName: undefined,
  },
};

export const useInboxUiStore = create<IInboxUiState>()((set) => ({
  ...INITIAL_STATE,
  setFilter: (filter) => set({ filter }),
  setScope: (scope) => set({ scope }),
  setSelectedTaskId: (id) => set({ selectedTaskId: id }),
  openActionModal: (taskId, decision, assetName) =>
    set({
      activeActionModal: {
        isOpen: true,
        taskId,
        decision,
        assetName,
      },
    }),
  closeActionModal: () =>
    set({
      activeActionModal: {
        isOpen: false,
        taskId: null,
        decision: null,
        assetName: undefined,
      },
    }),
  reset: () => set({ ...INITIAL_STATE }),
}));
