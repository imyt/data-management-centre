import { create } from "zustand";

export interface ISearchUiState {
  isOpen: boolean;
  query: string;
  setOpen: (open: boolean) => void;
  setQuery: (query: string) => void;
  toggleOpen: () => void;
  reset: () => void;
}

const INITIAL_STATE = {
  isOpen: false,
  query: "",
} as const;

export const useSearchUiStore = create<ISearchUiState>()((set) => ({
  ...INITIAL_STATE,
  setOpen: (open) => set({ isOpen: open }),
  setQuery: (query) => set({ query }),
  toggleOpen: () => set((s) => ({ isOpen: !s.isOpen })),
  reset: () => set({ ...INITIAL_STATE }),
}));
