import { create } from "zustand";

export interface ICatalogUiState {
  isCreateModalOpen: boolean;
  activeDrawerTab: "overview" | "editor" | "diff" | "history";
  setCreateModalOpen: (open: boolean) => void;
  setActiveDrawerTab: (tab: "overview" | "editor" | "diff" | "history") => void;
  reset: () => void;
}

const INITIAL_STATE = {
  isCreateModalOpen: false,
  activeDrawerTab: "overview",
} as const;

export const useCatalogUiStore = create<ICatalogUiState>()((set) => ({
  ...INITIAL_STATE,
  setCreateModalOpen: (open) => set({ isCreateModalOpen: open }),
  setActiveDrawerTab: (tab) => set({ activeDrawerTab: tab }),
  reset: () => set({ ...INITIAL_STATE }),
}));
