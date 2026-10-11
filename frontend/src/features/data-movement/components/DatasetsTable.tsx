import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Edit2, Trash2, Database, AlertCircle, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { listApplicationDatasetsOptions } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";
import { IsrBadge } from "./IsrBadge";

export const DatasetsTable: React.FC = () => {
  const {
    selectedAppHeadId,
    searchQuery,
    setSearchQuery,
    setCreateDatasetOpen,
    setEditingDatasetId,
    setDeletingDatasetId,
  } = useDataMovementUiStore();

  const { data: datasets = [], isLoading } = useQuery({
    ...listApplicationDatasetsOptions({
      path: { app_head_id: selectedAppHeadId || "" },
    }),
    enabled: Boolean(selectedAppHeadId),
  });

  const filteredDatasets = React.useMemo(() => {
    if (!searchQuery.trim()) return datasets;
    const q = searchQuery.toLowerCase();
    return datasets.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.business_context.toLowerCase().includes(q) ||
        (d.isr_classification && d.isr_classification.toLowerCase().includes(q)) ||
        (d.data_categories && d.data_categories.some((c) => c.toLowerCase().includes(q)))
    );
  }, [datasets, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
          <Input
            placeholder="Search datasets, data categories, ISR classification..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-xs bg-background"
          />
        </div>

        <Button
          size="sm"
          className="h-9 text-xs font-semibold shadow-xs gap-1.5"
          onClick={() => setCreateDatasetOpen(true)}
        >
          <Plus className="w-4 h-4" />
          Create Governed Dataset
        </Button>
      </div>

      {/* Datasets Table */}
      <div className="rounded-md border border-border bg-card overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-muted-foreground uppercase tracking-wider text-[11px] font-semibold">
                <th className="py-3 px-4">Dataset Name & Purpose</th>
                <th className="py-3 px-4">ISR Classification</th>
                <th className="py-3 px-4">Data Domain Categories</th>
                <th className="py-3 px-4 text-center">Active Usages</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted-foreground">
                    Loading application datasets...
                  </td>
                </tr>
              ) : filteredDatasets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted-foreground">
                    <Database className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
                    <p className="font-medium text-foreground">No datasets found</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Create a new application-scoped dataset to bind into technical integration flows.
                    </p>
                  </td>
                </tr>
              ) : (
                filteredDatasets.map((ds) => {
                  const hasUsages = (ds.usage_count || 0) > 0;
                  return (
                    <tr key={ds.id} className="hover:bg-muted/30 transition-colors group">
                      <td className="py-3.5 px-4 max-w-sm">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          {ds.name}
                        </div>
                        <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5 leading-relaxed">
                          {ds.business_context}
                        </p>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <IsrBadge classification={ds.isr_classification || "INTERNAL"} />
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {ds.data_categories && ds.data_categories.length > 0 ? (
                            ds.data_categories.map((cat) => (
                              <Badge
                                key={cat}
                                variant="outline"
                                className="text-[10px] font-mono px-1.5 py-0 bg-muted/60 text-muted-foreground"
                              >
                                {cat}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-[11px] text-muted-foreground italic">None specified</span>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        {hasUsages ? (
                          <Badge variant="secondary" className="font-mono text-[11px] bg-primary/10 text-primary border-primary/20 gap-1">
                            <Link2 className="w-3 h-3" />
                            {ds.usage_count} {ds.usage_count === 1 ? "Link" : "Links"}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="font-mono text-[11px] text-muted-foreground bg-muted/30">
                            0 Links
                          </Badge>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                            onClick={() => setEditingDatasetId(ds.id)}
                          >
                            <Edit2 className="w-3.5 h-3.5 mr-1" />
                            Edit
                          </Button>

                          {hasUsages ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span tabIndex={0}>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 text-xs text-muted-foreground/40 cursor-not-allowed hover:bg-transparent"
                                    onClick={() => setDeletingDatasetId(ds.id)}
                                  >
                                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                                    Delete
                                  </Button>
                                </span>
                              </TooltipTrigger>
                              <TooltipContent className="text-xs max-w-xs p-2">
                                <p className="font-semibold text-rose-500 flex items-center gap-1">
                                  <AlertCircle className="w-3.5 h-3.5" />
                                  Deletion Blocked (409)
                                </p>
                                <p className="text-[11px] mt-0.5 text-muted-foreground">
                                  Bound to {ds.usage_count} active integration(s). Unbind integrations before deleting.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 hover:text-rose-600"
                              onClick={() => setDeletingDatasetId(ds.id)}
                            >
                              <Trash2 className="w-3.5 h-3.5 mr-1" />
                              Delete
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
