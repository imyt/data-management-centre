import React, { useState, useEffect } from "react";
import {
  X,
  Lock,
  CheckCircle2,
  GitCompare,
  History,
  FileText,
  Save,
  Sparkles,
  GitFork,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  AssetHead,
  AssetType,
} from "@/api/client";
import {
  getVisualDiffApiV1AssetsAssetHeadIdDiffGetOptions,
  getVersionHistoryApiV1AssetsAssetHeadIdHistoryGetOptions,
  acquireOrForkDraftApiV1AssetsAssetHeadIdDraftPostMutation,
  updateDraftApiV1AssetsAssetHeadIdDraftPutMutation,
  publishAssetVersionApiV1AssetsAssetHeadIdPublishPostMutation,
  releaseLockApiV1AssetsAssetHeadIdDraftReleaseLockPostMutation,
} from "@/api/client";
import { LineageGraph } from "./LineageGraph";
import { DynamicAttributeForm } from "./DynamicAttributeForm";
import { Button } from "@/components/ui/button";

export interface IInspectDrawerProps {
  assetHead: AssetHead | null;
  assetTypes: AssetType[];
  onClose: () => void;
  onAssetUpdated?: () => void;
}

export const InspectDrawer: React.FC<IInspectDrawerProps> = ({
  assetHead,
  assetTypes,
  onClose,
  onAssetUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "edit" | "diff" | "history" | "lineage">("overview");
  const [error, setError] = useState<string | null>(null);

  // Edit draft form state
  const [draftName, setDraftName] = useState("");
  const [draftMarkdown, setDraftMarkdown] = useState("");
  const [draftAttributes, setDraftAttributes] = useState<Record<string, any>>({});

  const queryClient = useQueryClient();

  // React Query queries powered directly by Hey-API options
  const { data: diffData } = useQuery({
    ...getVisualDiffApiV1AssetsAssetHeadIdDiffGetOptions({
      path: { asset_head_id: assetHead?.id || "" },
    }),
    enabled: !!assetHead?.id && activeTab === "diff",
  });

  const { data: history = [] } = useQuery({
    ...getVersionHistoryApiV1AssetsAssetHeadIdHistoryGetOptions({
      path: { asset_head_id: assetHead?.id || "" },
    }),
    enabled: !!assetHead?.id && activeTab === "history",
  });

  // Mutations powered directly by Hey-API mutation options
  const acquireMutation = useMutation({
    ...acquireOrForkDraftApiV1AssetsAssetHeadIdDraftPostMutation(),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const updateMutation = useMutation({
    ...updateDraftApiV1AssetsAssetHeadIdDraftPutMutation(),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const publishMutation = useMutation({
    ...publishAssetVersionApiV1AssetsAssetHeadIdPublishPostMutation(),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const releaseMutation = useMutation({
    ...releaseLockApiV1AssetsAssetHeadIdDraftReleaseLockPostMutation(),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const isMutating =
    acquireMutation.isPending ||
    updateMutation.isPending ||
    publishMutation.isPending ||
    releaseMutation.isPending;

  // Synchronize on asset selection
  useEffect(() => {
    if (!assetHead) return;
    setError(null);

    const activeVersion = assetHead.active_draft_version || assetHead.published_version;
    if (activeVersion) {
      setDraftName(activeVersion.name);
      setDraftMarkdown(activeVersion.description_markdown || "");
      setDraftAttributes(activeVersion.attributes_payload || {});
    }
  }, [assetHead]);

  if (!assetHead) return null;

  const currentVersion = assetHead.active_draft_version || assetHead.published_version;
  const assetType = assetTypes.find((t) => t.id === assetHead.asset_type_id);

  const handleAcquireDraft = async () => {
    setError(null);
    try {
      await acquireMutation.mutateAsync({
        path: { asset_head_id: assetHead.id },
      });
      onAssetUpdated?.();
      setActiveTab("edit");
    } catch (err: any) {
      setError(err.message || "Failed to acquire draft lock");
    }
  };

  const handleSaveDraft = async () => {
    setError(null);
    try {
      await updateMutation.mutateAsync({
        path: { asset_head_id: assetHead.id },
        body: {
          name: draftName,
          description_markdown: draftMarkdown,
          attributes_payload: draftAttributes,
        },
      });
      onAssetUpdated?.();
      setActiveTab("overview");
    } catch (err: any) {
      setError(err.message || "Failed to save draft");
    }
  };

  const handleReleaseLock = async () => {
    setError(null);
    try {
      await releaseMutation.mutateAsync({
        path: { asset_head_id: assetHead.id },
      });
      onAssetUpdated?.();
    } catch (err: any) {
      setError(err.message || "Failed to release lock");
    }
  };

  const handlePublish = async () => {
    setError(null);
    try {
      await publishMutation.mutateAsync({
        path: { asset_head_id: assetHead.id },
      });
      onAssetUpdated?.();
      setActiveTab("overview");
    } catch (err: any) {
      setError(err.message || "Failed to publish version");
    }
  };

  return (
    <aside className="w-96 lg:w-[480px] border-l border-border bg-card flex flex-col h-full shrink-0 select-none shadow-xl z-20">
      {/* Drawer Header */}
      <div className="h-11 px-3 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
        <div className="flex items-center space-x-2 truncate">
          <span className="font-bold text-xs truncate text-foreground">
            {currentVersion?.name || "Asset Details"}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
            v{currentVersion?.version_number}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center border-b border-border px-3 bg-card shrink-0">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center space-x-1.5 py-2 px-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === "overview"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>

        <button
          onClick={() => {
            setActiveTab("edit");
            if (!assetHead.active_draft_version_id) handleAcquireDraft();
          }}
          className={`flex items-center space-x-1.5 py-2 px-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === "edit"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Lock className="w-3.5 h-3.5" />
          <span>Draft Editor</span>
        </button>

        <button
          onClick={() => setActiveTab("diff")}
          className={`flex items-center space-x-1.5 py-2 px-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === "diff"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <GitCompare className="w-3.5 h-3.5" />
          <span>Visual Diff</span>
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center space-x-1.5 py-2 px-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === "history"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Audit Ledger</span>
        </button>

        <button
          onClick={() => setActiveTab("lineage")}
          className={`flex items-center space-x-1.5 py-2 px-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === "lineage"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <GitFork className="w-3.5 h-3.5" />
          <span>Lineage DAG</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-2 bg-destructive/10 border-b border-destructive/20 text-destructive text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="underline text-[10px] cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            {/* Metamodel Type and Status Bar */}
            <div className="flex items-center justify-between p-2.5 bg-muted/40 rounded border border-border">
              <div>
                <span className="text-[10px] text-muted-foreground uppercase font-medium">Type</span>
                <p className="font-semibold text-xs text-foreground">{assetType?.name || "Business Term"}</p>
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground uppercase font-medium">Status</span>
                <p className="font-semibold text-xs text-primary">{currentVersion?.status}</p>
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground uppercase font-medium">Version</span>
                <p className="font-semibold text-xs font-mono">v{currentVersion?.version_number}</p>
              </div>
            </div>

            {/* Markdown Description */}
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground">Definition (Markdown)</span>
              <div className="p-3 rounded bg-muted/20 border border-border text-xs text-foreground whitespace-pre-wrap leading-relaxed">
                {currentVersion?.description_markdown || "No markdown definition provided."}
              </div>
            </div>

            {/* Attributes Section */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground">Configured Attributes</span>
              <div className="space-y-1.5 border border-border rounded divide-y divide-border/60">
                {Object.entries(currentVersion?.attributes_payload || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between p-2 text-xs">
                    <span className="text-muted-foreground font-medium">{key}</span>
                    <span className="font-semibold text-foreground font-mono">
                      {typeof value === "boolean" ? (value ? "TRUE" : "FALSE") : String(value)}
                    </span>
                  </div>
                ))}
                {Object.keys(currentVersion?.attributes_payload || {}).length === 0 && (
                  <div className="p-3 text-center text-muted-foreground text-xs">
                    No custom attributes assigned.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* DRAFT EDITOR TAB */}
        {activeTab === "edit" && (
          <div className="space-y-3">
            <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded flex items-center justify-between text-xs text-amber-600 dark:text-amber-400">
              <div className="flex items-center space-x-1.5">
                <Lock className="w-3.5 h-3.5" />
                <span>Exclusive Edit Lease Active</span>
              </div>
              <button
                onClick={handleReleaseLock}
                disabled={isMutating}
                className="text-[10px] underline hover:no-underline cursor-pointer"
              >
                Release Lease
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Asset Name</label>
              <input
                type="text"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-muted/40 border border-border rounded text-xs text-foreground outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Markdown Description</label>
              <textarea
                rows={6}
                value={draftMarkdown}
                onChange={(e) => setDraftMarkdown(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-muted/40 border border-border rounded text-xs text-foreground outline-none focus:border-primary font-mono text-[11px]"
              />
            </div>

            {/* Dynamic Attributes Inputs */}
            <div className="space-y-2 pt-1 border-t border-border">
              <span className="text-xs font-semibold text-foreground">Attributes</span>
              <DynamicAttributeForm
                assetType={assetType}
                values={draftAttributes}
                onChange={setDraftAttributes}
              />
            </div>
          </div>
        )}

        {/* VISUAL DIFF TAB */}
        {activeTab === "diff" && (
          <div className="space-y-4">
            {!diffData ? (
              <div className="py-8 text-center text-muted-foreground text-xs">
                No active working draft to compare against published version.
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-2 bg-primary/10 border border-primary/20 rounded flex items-center justify-between text-xs text-primary font-medium">
                  <span>Change Detection Engine</span>
                  <span>{diffData.has_changes ? "Pending Mutations" : "Identical State"}</span>
                </div>

                {/* Name Diff */}
                {(() => {
                  const nameDiff = diffData.name_diff as { changed?: boolean; old_name?: string; new_name?: string };
                  const descDiff = diffData.description_diff as { has_changes?: boolean; unified_diff?: string[] };
                  const unifiedDiff = descDiff?.unified_diff || [];

                  return (
                    <>
                      {nameDiff?.changed && (
                        <div className="p-2 bg-muted/30 border border-border rounded text-xs space-y-1">
                          <span className="text-[10px] text-muted-foreground uppercase font-medium">Name Modified</span>
                          <div className="text-red-500 line-through text-[11px]">{String(nameDiff.old_name)}</div>
                          <div className="text-emerald-500 font-semibold text-[11px]">{String(nameDiff.new_name)}</div>
                        </div>
                      )}

                      {/* Attributes Diff */}
                      <div className="space-y-1.5">
                        <span className="text-xs font-semibold text-foreground">Attribute Mutations</span>
                        <div className="space-y-1.5">
                          {diffData.attributes_diff.map((attr) => (
                            <div
                              key={attr.attribute_code}
                              className="p-2 rounded border border-border flex items-center justify-between text-xs bg-card"
                            >
                              <span className="font-medium text-foreground">{attr.attribute_code}</span>
                              <div className="flex items-center space-x-1.5">
                                {attr.change_type === "MODIFIED" && (
                                  <>
                                    <span className="text-red-500 line-through font-mono text-[11px]">
                                      {String(attr.old_value)}
                                    </span>
                                    <span className="text-muted-foreground">→</span>
                                    <span className="text-emerald-500 font-bold font-mono text-[11px]">
                                      {String(attr.new_value)}
                                    </span>
                                  </>
                                )}
                                {attr.change_type === "ADDED" && (
                                  <span className="text-emerald-500 font-bold font-mono text-[11px]">
                                    +{String(attr.new_value)}
                                  </span>
                                )}
                                {attr.change_type === "UNCHANGED" && (
                                  <span className="text-muted-foreground font-mono text-[11px]">
                                    {String(attr.new_value)}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Markdown Diff Preview */}
                      {descDiff?.has_changes && (
                        <div className="space-y-1.5">
                          <span className="text-xs font-semibold text-foreground">Description Diff</span>
                          <div className="p-2 bg-muted/40 border border-border rounded font-mono text-[10px] space-y-0.5 overflow-x-auto">
                            {unifiedDiff.map((line: string, idx: number) => (
                              <div
                                key={idx}
                                className={
                                  line.startsWith("+")
                                    ? "text-emerald-500 font-semibold"
                                    : line.startsWith("-")
                                    ? "text-red-500 line-through"
                                    : "text-muted-foreground"
                                }
                              >
                                {line}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* AUDIT LEDGER TAB */}
        {activeTab === "history" && (
          <div className="space-y-2">
            <span className="text-xs font-semibold text-foreground">Chronological Version Ledger</span>
            <div className="space-y-2">
              {history.map((ver) => (
                <div
                  key={ver.id}
                  className="p-2.5 rounded border border-border bg-card space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-foreground font-mono">v{ver.version_number}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        ver.status === "PUBLISHED"
                          ? "bg-emerald-500/10 text-emerald-500"
                          : ver.status === "SUPERSEDED"
                          ? "bg-slate-500/10 text-muted-foreground"
                          : "bg-amber-500/10 text-amber-500"
                      }`}
                    >
                      {ver.status}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-[11px] truncate">{ver.name}</p>
                  <p className="text-muted-foreground/60 text-[10px]">
                    Created: {new Date(ver.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* LINEAGE GRAPH TAB */}
        {activeTab === "lineage" && (
          <div className="h-[580px] -m-4">
            <LineageGraph assetHeadId={assetHead.id} assetHead={assetHead} />
          </div>
        )}
      </div>

      {/* Drawer Action Footer */}
      <div className="h-12 border-t border-border px-3 bg-card flex items-center justify-between shrink-0">
        {assetHead.active_draft_version_id ? (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveDraft}
              disabled={isMutating}
              className="h-8 text-xs font-medium gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{updateMutation.isPending ? "Saving..." : "Save Draft"}</span>
            </Button>

            <Button
              size="sm"
              onClick={handlePublish}
              disabled={isMutating}
              className="h-8 text-xs font-medium gap-1.5 shadow-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{publishMutation.isPending ? "Publishing..." : "Publish to Production"}</span>
            </Button>
          </>
        ) : (
          <Button
            size="sm"
            onClick={handleAcquireDraft}
            disabled={isMutating}
            className="w-full h-8 text-xs font-medium gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{acquireMutation.isPending ? "Acquiring..." : "Fork Working Draft (Acquire Lock)"}</span>
          </Button>
        )}
      </div>
    </aside>
  );
};
