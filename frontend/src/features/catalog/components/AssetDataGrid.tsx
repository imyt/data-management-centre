import React from "react";
import {
  Lock,
  Plus,
  BookOpen,
  ShieldCheck,
  Server,
  BarChart3,
  Activity,
  FileQuestion,
  Search,
} from "lucide-react";
import type { AssetHead, AssetType } from "@/api/client";

interface AssetDataGridProps {
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

export const AssetDataGrid: React.FC<AssetDataGridProps> = ({
  assets,
  assetTypes,
  selectedAssetId,
  onSelectAsset,
  onOpenCreateModal,
  searchFilter,
  onSearchChange,
  statusFilter,
  onStatusChange,
}) => {
  const getAssetTypeIcon = (code: string) => {
    switch (code) {
      case "BUSINESS_TERM":
        return <BookOpen className="w-3.5 h-3.5 text-blue-500" />;
      case "DATA_POLICY":
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />;
      case "APPLICATION":
        return <Server className="w-3.5 h-3.5 text-purple-500" />;
      case "REPORT":
        return <BarChart3 className="w-3.5 h-3.5 text-cyan-500" />;
      case "METRIC":
        return <Activity className="w-3.5 h-3.5 text-amber-500" />;
      default:
        return <FileQuestion className="w-3.5 h-3.5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PUBLISHED":
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            PUBLISHED
          </span>
        );
      case "DRAFT":
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            DRAFT
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20">
            UNDER REVIEW
          </span>
        );
      case "SUPERSEDED":
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-500/10 text-slate-500 border border-slate-500/20">
            SUPERSEDED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground border border-border">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Grid Toolbar */}
      <div className="h-9 px-3 border-b border-border bg-card flex items-center justify-between shrink-0 space-x-2">
        <div className="flex items-center space-x-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-2 top-2.5 text-muted-foreground" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Filter grid assets..."
              className="w-full pl-7 pr-3 py-1 bg-muted/40 border border-border rounded text-xs text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            className="px-2 py-1 bg-muted/40 border border-border rounded text-xs text-foreground outline-none cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="PUBLISHED">Published</option>
            <option value="DRAFT">Draft</option>
            <option value="UNDER_REVIEW">Under Review</option>
          </select>
        </div>

        <button
          onClick={onOpenCreateModal}
          className="flex items-center space-x-1.5 px-2.5 py-1 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-medium transition-colors shadow-xs cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Propose Asset</span>
        </button>
      </div>

      {/* Grid Table Container */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-muted/50 sticky top-0 border-b border-border text-[11px] font-medium text-muted-foreground select-none">
            <tr>
              <th className="py-2 px-3 w-10">Type</th>
              <th className="py-2 px-3">Asset Name & Summary</th>
              <th className="py-2 px-3 w-28">Status</th>
              <th className="py-2 px-3 w-20 text-center">Version</th>
              <th className="py-2 px-3 w-40">Classifications</th>
              <th className="py-2 px-3 w-32">Lock / Lease</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {assets.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-muted-foreground text-xs">
                  No assets found in this governance scope.
                </td>
              </tr>
            ) : (
              assets.map((asset) => {
                const isSelected = selectedAssetId === asset.id;
                const activeVersion = asset.published_version || asset.active_draft_version;
                const typeObj = assetTypes.find((t) => t.id === asset.asset_type_id);
                const typeCode = typeObj?.code || "BUSINESS_TERM";
                const isLocked = !!asset.locked_by_user_id;

                const attrs = (activeVersion?.attributes_payload as Record<string, unknown>) || {};
                const confRaw = attrs["CONFIDENTIALITY"] || attrs["Confidentiality"];
                const confidentiality = confRaw ? String(confRaw) : null;
                const pii = Boolean(attrs["PII"]);

                return (
                  <tr
                    key={asset.id}
                    onClick={() => onSelectAsset(asset)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-primary/10 hover:bg-primary/15 font-medium"
                        : "hover:bg-accent/40"
                    }`}
                  >
                    {/* Type Icon */}
                    <td className="py-2 px-3 text-center">
                      <div className="flex items-center justify-center">
                        {getAssetTypeIcon(typeCode)}
                      </div>
                    </td>

                    {/* Name & Markdown snippet */}
                    <td className="py-2 px-3 max-w-xs md:max-w-md">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-foreground truncate">
                          {activeVersion?.name || "Untitled Asset"}
                        </span>
                        {asset.active_draft_version_id && asset.published_version_id && (
                          <span className="text-[9px] px-1 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded font-mono">
                            DRAFTING
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate font-normal">
                        {activeVersion?.description_markdown || "No markdown description provided."}
                      </p>
                    </td>

                    {/* Status */}
                    <td className="py-2 px-3">
                      {getStatusBadge(activeVersion?.status || "DRAFT")}
                    </td>

                    {/* Version Badge */}
                    <td className="py-2 px-3 text-center font-mono text-[11px] text-muted-foreground">
                      v{activeVersion?.version_number ?? 1}
                    </td>

                    {/* Metadata & Tag Badges */}
                    <td className="py-2 px-3">
                      <div className="flex items-center space-x-1 flex-wrap gap-y-1">
                        {confidentiality && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-muted text-muted-foreground border border-border">
                            {confidentiality}
                          </span>
                        )}
                        {pii && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 font-semibold">
                            PII
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Exclusive Edit Lease State */}
                    <td className="py-2 px-3">
                      {isLocked ? (
                        <div className="flex items-center space-x-1 text-amber-600 dark:text-amber-400 text-[11px]">
                          <Lock className="w-3 h-3" />
                          <span>Under revision</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground/60 text-[11px]">Unlocked</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Grid Footer Counter */}
      <div className="h-7 px-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground bg-card shrink-0">
        <span>Total Records: {assets.length}</span>
        <span className="font-mono text-[10px]">PostgreSQL 18 GIN Indexing Active</span>
      </div>
    </div>
  );
};
