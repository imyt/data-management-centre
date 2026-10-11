import type { AssetHead, AssetType, Community } from "@/api/client";

export interface ICatalogSearchParams {
  domainId?: string;
  assetId?: string;
  search?: string;
  status?: string;
}

export interface ICommunityTreeProps {
  communities: Community[];
  selectedDomainId: string | null;
  onSelectDomain: (domain: { id: string; name: string } | null) => void;
}

export interface IAssetDataGridProps {
  assets: AssetHead[];
  assetTypes: AssetType[];
  selectedAssetId: string | null;
  onSelectAsset: (asset: AssetHead) => void;
  onOpenCreateModal: () => void;
  searchFilter: string;
  onSearchChange: (search: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
}

export interface IInspectDrawerProps {
  assetHead: AssetHead;
  assetTypes: AssetType[];
  onClose: () => void;
}

export interface ICreateAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  domains: Array<{ id: string; name: string }>;
  assetTypes: AssetType[];
}

export type {
  ILineageNode,
  ILineageEdge,
  ILineageGraphData,
  ILineageGraphProps,
} from "../components/LineageGraph";
