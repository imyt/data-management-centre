/**
 * Public contract for Catalog feature module.
 * Other modules and routing layers MUST only import through this barrel.
 */

// Pages
export { CatalogPage } from "./pages/catalog-page";

// Components
export { CommunityTree } from "./components/CommunityTree";
export { AssetDataGrid } from "./components/AssetDataGrid";
export { InspectDrawer } from "./components/InspectDrawer";
export { CreateAssetModal } from "./components/CreateAssetModal";
export { DynamicAttributeForm } from "./components/DynamicAttributeForm";
export type { DynamicAttributeFormProps } from "./components/DynamicAttributeForm";
export { LineageGraph } from "./components/LineageGraph";
export type {
  ILineageGraphProps,
  ILineageNode,
  ILineageEdge,
  ILineageGraphData,
} from "./components/LineageGraph";

// UI Store
export { useCatalogUiStore } from "./stores/catalog.store";
export type { ICatalogUiState } from "./stores/catalog.store";

// Types
export type {
  ICatalogSearchParams,
  ICommunityTreeProps,
  IAssetDataGridProps,
  IInspectDrawerProps,
  ICreateAssetModalProps,
} from "./types";
