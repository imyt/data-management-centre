/**
 * Public contract for Search feature module.
 * Other modules and routing layers MUST only import through this barrel.
 */

// Components
export { CommandPalette } from "./components/CommandPalette";
export type { ICommandPaletteProps } from "./components/CommandPalette";

// UI Store
export { useSearchUiStore } from "./stores/search.store";
export type { ISearchUiState } from "./stores/search.store";
