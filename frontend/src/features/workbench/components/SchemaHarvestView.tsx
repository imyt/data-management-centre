import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Table as TableIcon, Columns, AlertTriangle, CheckCircle2, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { workbenchApi } from "../api/workbenchApi";

interface SchemaHarvestViewProps {
  appHeadId: string;
}

export const SchemaHarvestView: React.FC<SchemaHarvestViewProps> = ({ appHeadId }) => {
  const queryClient = useQueryClient();
  const [selectedTableId, setSelectedTableId] = useState<string>("ALL");
  const [driftFilter, setDriftFilter] = useState<string>("ALL");

  const { data: tables = [] } = useQuery({
    queryKey: ["physical-tables", appHeadId],
    queryFn: () => workbenchApi.listTables(appHeadId),
    enabled: !!appHeadId,
  });

  const { data: columns = [] } = useQuery({
    queryKey: ["physical-columns", appHeadId, selectedTableId, driftFilter],
    queryFn: () =>
      workbenchApi.listColumns(appHeadId, {
        table_id: selectedTableId !== "ALL" ? selectedTableId : undefined,
        drift_status: driftFilter !== "ALL" ? driftFilter : undefined,
      }),
    enabled: !!appHeadId,
  });

  const harvestMutation = useMutation({
    mutationFn: () => workbenchApi.triggerHarvest(appHeadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["physical-tables", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["physical-columns", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues", appHeadId] });
    },
  });

  const unclassifiedColumns = columns.filter((c) => c.drift_status === "ADDED_UNCLASSIFIED");

  return (
    <div className="space-y-6">
      {/* Header & Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-foreground tracking-tight flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            <span>Schema Harvesting & Column-Grain Drift Engine</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Physical database tables and columns harvested from underlying storage engines. Detects unclassified drift in real time.
          </p>
        </div>

        <Button
          size="sm"
          disabled={harvestMutation.isPending}
          onClick={() => harvestMutation.mutate()}
          className="text-xs h-8 gap-1.5 font-bold shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${harvestMutation.isPending ? "animate-spin" : ""}`} />
          <span>{harvestMutation.isPending ? "Harvesting Engine..." : "Harvest Schema Now"}</span>
        </Button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <TableIcon className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Harvested Tables</div>
            <div className="text-base font-bold font-mono text-foreground">{tables.length} Active Tables</div>
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Columns className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Physical Columns</div>
            <div className="text-base font-bold font-mono text-foreground">{columns.length} Total Fields</div>
          </div>
        </div>

        <div className={`border p-4 rounded-xl flex items-center gap-3 ${
          unclassifiedColumns.length > 0
            ? "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400"
            : "bg-card border-border text-foreground"
        }`}>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
            unclassifiedColumns.length > 0 ? "bg-amber-500/20 text-amber-600 dark:text-amber-400" : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          }`}>
            {unclassifiedColumns.length > 0 ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Unclassified Schema Drift</div>
            <div className="text-base font-bold font-mono">
              {unclassifiedColumns.length > 0 ? `${unclassifiedColumns.length} Columns Drifted` : "0 Drift Detected"}
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Table Explorer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <Select value={selectedTableId} onValueChange={(val) => setSelectedTableId(val)}>
              <SelectTrigger className="h-8 text-xs w-48 bg-background">
                <SelectValue placeholder="Filter Table..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  All Harvested Tables ({tables.length})
                </SelectItem>
                {tables.map((t) => (
                  <SelectItem key={t.id} value={t.id} className="text-xs">
                    {t.schema_name}.{t.table_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={driftFilter} onValueChange={(val) => setDriftFilter(val)}>
              <SelectTrigger className="h-8 text-xs w-44 bg-background">
                <SelectValue placeholder="Drift Status..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  All Drift States
                </SelectItem>
                <SelectItem value="ADDED_UNCLASSIFIED" className="text-xs font-semibold text-amber-600">
                  Unclassified Drift
                </SelectItem>
                <SelectItem value="SYNCED" className="text-xs">
                  Synced Baseline
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="text-xs text-muted-foreground font-mono">
            Atomic Column Grain Governance
          </div>
        </div>

        {/* Columns Table */}
        <Card className="border-border bg-card">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs font-semibold">Physical Field</TableHead>
                  <TableHead className="text-xs font-semibold">Data Type</TableHead>
                  <TableHead className="text-xs font-semibold">Drift State</TableHead>
                  <TableHead className="text-xs font-semibold">PII Indicator</TableHead>
                  <TableHead className="text-xs font-semibold">Dynamic Masking</TableHead>
                  <TableHead className="text-xs font-semibold">ISR Tier</TableHead>
                  <TableHead className="text-xs font-semibold">Business Term</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {columns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-6 text-xs text-muted-foreground">
                      No columns match the selected filter.
                    </TableCell>
                  </TableRow>
                ) : (
                  columns.map((col) => {
                    const isDrifted = col.drift_status === "ADDED_UNCLASSIFIED";

                    return (
                      <TableRow
                        key={col.id}
                        className={`text-xs ${isDrifted ? "bg-amber-500/10 hover:bg-amber-500/15" : ""}`}
                      >
                        <TableCell className="font-semibold text-foreground">
                          <div className="flex items-center gap-1.5 font-mono">
                            <span className="text-muted-foreground font-normal">{col.table_name}.</span>
                            <span className="text-foreground">{col.column_name}</span>
                          </div>
                        </TableCell>

                        <TableCell className="font-mono text-muted-foreground">
                          {col.data_type}
                        </TableCell>

                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`text-[10px] font-mono font-bold ${
                              isDrifted
                                ? "bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/40 animate-pulse"
                                : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                            }`}
                          >
                            {col.drift_status}
                          </Badge>
                        </TableCell>

                        <TableCell>
                          {col.is_pii ? (
                            <Badge variant="destructive" className="text-[10px] font-mono">
                              PII
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">—</span>
                          )}
                        </TableCell>

                        <TableCell className="font-mono text-muted-foreground">
                          {col.masking_strategy}
                        </TableCell>

                        <TableCell>
                          <Badge variant="outline" className="text-[10px] font-mono bg-muted/50">
                            {col.isr_classification}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-muted-foreground truncate max-w-xs">
                          {col.business_term_name || <span className="italic text-muted-foreground/50">Unlinked</span>}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
