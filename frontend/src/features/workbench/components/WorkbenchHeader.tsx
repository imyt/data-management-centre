import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Server, RefreshCw, User } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listApplicationsOptions } from "@/api/client";
import { useWorkbenchUiStore } from "../stores/workbench.store";
import type { WorkbenchSummary } from "../types";

interface WorkbenchHeaderProps {
  summary?: WorkbenchSummary;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const WorkbenchHeader: React.FC<WorkbenchHeaderProps> = ({
  summary,
  onRefresh,
  isRefreshing,
}) => {
  const { selectedAppHeadId, setSelectedAppHeadId } = useWorkbenchUiStore();

  const { data: applications = [] } = useQuery({
    ...listApplicationsOptions(),
  });

  // Auto-select first app if none selected
  React.useEffect(() => {
    if (!selectedAppHeadId && applications.length > 0) {
      setSelectedAppHeadId(applications[0].asset_head_id);
    }
  }, [selectedAppHeadId, applications, setSelectedAppHeadId]);

  const currentApp = applications.find((a) => a.asset_head_id === selectedAppHeadId) || applications[0];

  return (
    <div className="bg-card border-b border-border px-6 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0 shadow-xs">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
          <Server className="w-5 h-5" />
        </div>

        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-base font-bold text-foreground tracking-tight">
              {summary?.application.itsm_system_name || currentApp?.itsm_system_name || "Application Workbench"}
            </h1>
            <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground bg-muted/60">
              CI: {summary?.application.itsm_system_id || currentApp?.itsm_system_id || "APP-UNKNOWN"}
            </Badge>
            <Badge
              variant={summary?.application.cmdb_criticality === "TIER_1" ? "destructive" : "secondary"}
              className="text-[10px] font-mono font-semibold"
            >
              {summary?.application.cmdb_criticality || "TIER_2"}
            </Badge>
            <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              ITSM Synced
            </span>
          </div>

          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1 flex-wrap">
            <span className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" />
              Application Owner:{" "}
              <strong className="text-foreground font-semibold">
                {summary?.application.app_owner_name || currentApp?.app_owner_name || "Elena Rostova"}
              </strong>
            </span>
            <span className="text-muted-foreground/60">•</span>
            <span>
              Synced:{" "}
              <span className="font-mono text-muted-foreground">
                {summary?.application.synced_at
                  ? new Date(summary.application.synced_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : "Just now"}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* Application Switcher & Actions */}
      <div className="flex items-center gap-3">
        <div className="w-64">
          <Select
            value={selectedAppHeadId || currentApp?.asset_head_id || ""}
            onValueChange={(val) => setSelectedAppHeadId(val)}
          >
            <SelectTrigger className="h-8 text-xs bg-background">
              <SelectValue placeholder="Switch Application..." />
            </SelectTrigger>
            <SelectContent>
              {applications.map((app) => (
                <SelectItem key={app.asset_head_id} value={app.asset_head_id} className="text-xs">
                  <div className="flex items-center justify-between w-full gap-2">
                    <span className="font-medium truncate">{app.itsm_system_name}</span>
                    <span className="text-[10px] font-mono text-muted-foreground">({app.itsm_system_id})</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="h-8 text-xs gap-1.5"
          title="Synchronize technical topology with ServiceNow CMDB"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>Sync CMDB</span>
        </Button>
      </div>
    </div>
  );
};
