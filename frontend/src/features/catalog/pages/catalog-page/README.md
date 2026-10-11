# Catalog Page (`/catalog`)

## Overview
Primary curated data catalog view featuring three synchronized functional panes:
1. **Community Hierarchy Tree**: Browse organizational communities and sub-domains.
2. **Asset Data Grid**: High-density virtualized list with type badges, status chips, version indicators, and lease indicators.
3. **Inspect Drawer**: Deep-dive sheet with draft editing, visual semantic diff, and audit version history.

## Route & Parameters
- **Path**: `/catalog`
- **Query Parameters**:
  - `domainId?: string` — active organizational domain scope filter
  - `assetId?: string` — active inspected asset head ID (opens right drawer)
  - `search?: string` — search query filtering asset names
  - `status?: string` — version lifecycle status filter (`ALL`, `DRAFT`, `PUBLISHED`, `SUPERSEDED`)

## Data Dependencies
- `listCommunitiesApiV1CommunitiesGetOptions` — loads organizational communities
- `listAssetTypesApiV1MetamodelAssetTypesGetOptions` — loads metamodel classification types
- `listAssetsApiV1AssetsGetOptions` — filtered catalog asset heads
- `getAssetApiV1AssetsAssetHeadIdGetOptions` — single asset details for drawer inspection

## UI State
- `useCatalogUiStore`: Manages creation modal state and active drawer tab selection.
