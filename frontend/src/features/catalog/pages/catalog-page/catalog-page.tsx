import React from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { CommunityTree } from "../../components/CommunityTree";
import { AssetDataGrid } from "../../components/AssetDataGrid";
import { InspectDrawer } from "../../components/InspectDrawer";
import { useCatalogUiStore } from "../../stores/catalog.store";
import { catalogPageStyles } from "./catalog-page.styles";
import {
  listCommunitiesApiV1CommunitiesGetOptions,
  listAssetTypesApiV1MetamodelAssetTypesGetOptions,
  listAssetsApiV1AssetsGetOptions,
  getAssetApiV1AssetsAssetHeadIdGetOptions,
} from "@/api/client";
import type { CatalogSearch } from "@/router";

export const CatalogPage: React.FC = () => {
  const searchParams = useSearch({ from: "/catalog" }) as CatalogSearch;
  const navigate = useNavigate({ from: "/catalog" });
  const setCreateModalOpen = useCatalogUiStore((s) => s.setCreateModalOpen);

  const domainId = searchParams.domainId;
  const assetId = searchParams.assetId;
  const searchFilter = searchParams.search || "";
  const statusFilter = searchParams.status || "ALL";

  // Server state: React Query cached queries via Hey-API generated query options
  const { data: communities = [] } = useQuery(listCommunitiesApiV1CommunitiesGetOptions());
  const { data: assetTypes = [] } = useQuery(listAssetTypesApiV1MetamodelAssetTypesGetOptions());
  const { data: assets = [] } = useQuery(
    listAssetsApiV1AssetsGetOptions({
      query: {
        domain_id: domainId,
        search: searchFilter || undefined,
      },
    })
  );

  // Server state: Query specific asset details for drawer if assetId is set
  const { data: selectedAssetDetail } = useQuery({
    ...getAssetApiV1AssetsAssetHeadIdGetOptions({
      path: { asset_head_id: assetId || "" },
    }),
    enabled: !!assetId,
  });

  const selectedAsset =
    selectedAssetDetail || (assetId ? assets.find((a) => a.id === assetId) || null : null);

  const filteredAssets = assets.filter((asset) => {
    if (statusFilter === "ALL") return true;
    const version = asset.published_version || asset.active_draft_version;
    return version?.status === statusFilter;
  });

  return (
    <div className={catalogPageStyles.container}>
      {/* Pane 1: Community and Organizational Hierarchy */}
      <CommunityTree
        communities={communities}
        selectedDomainId={domainId || null}
        onSelectDomain={(dom) => {
          navigate({
            search: (prev) => ({
              ...prev,
              domainId: dom?.id,
              assetId: undefined,
            }),
          });
        }}
      />

      {/* Pane 2: High-Density Catalog Data Grid */}
      <AssetDataGrid
        assets={filteredAssets}
        assetTypes={assetTypes}
        selectedAssetId={assetId || null}
        onSelectAsset={(asset) => {
          navigate({
            search: (prev) => ({
              ...prev,
              assetId: asset.id,
            }),
          });
        }}
        onOpenCreateModal={() => setCreateModalOpen(true)}
        searchFilter={searchFilter}
        onSearchChange={(search) => {
          navigate({
            search: (prev) => ({
              ...prev,
              search: search || undefined,
            }),
          });
        }}
        statusFilter={statusFilter}
        onStatusChange={(status) => {
          navigate({
            search: (prev) => ({
              ...prev,
              status: status || undefined,
            }),
          });
        }}
      />

      {/* Pane 3: Right Side Inspect / Visual Diff Drawer */}
      {assetId && selectedAsset && (
        <InspectDrawer
          assetHead={selectedAsset}
          assetTypes={assetTypes}
          onClose={() => {
            navigate({
              search: (prev) => ({
                ...prev,
                assetId: undefined,
              }),
            });
          }}
        />
      )}
    </div>
  );
};
