import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Server, ExternalLink, Database, ArrowRightLeft, User } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { listApplicationsOptions } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

export const ApplicationProfileBanner: React.FC = () => {
  const { selectedAppHeadId, setSelectedAppHeadId } = useDataMovementUiStore();

  const { data: applications = [], isLoading } = useQuery({
    ...listApplicationsOptions(),
  });

  // Auto-select first application if none selected
  React.useEffect(() => {
    if (!selectedAppHeadId && applications.length > 0) {
      setSelectedAppHeadId(applications[0].asset_head_id);
    }
  }, [selectedAppHeadId, applications, setSelectedAppHeadId]);

  const currentApp = applications.find((a) => a.asset_head_id === selectedAppHeadId) || applications[0];

  if (isLoading || !currentApp) {
    return (
      <div className="h-20 bg-muted/40 border-b border-border animate-pulse p-4 flex items-center justify-between" />
    );
  }

  return (
    <div className="bg-card border-b border-border px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0 shadow-xs">
      <div className="flex items-start md:items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
          <Server className="w-5 h-5" />
        </div>

        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-bold text-foreground tracking-tight">
              {currentApp.itsm_system_name}
            </h1>
            <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground bg-muted/50">
              ITSM: {currentApp.itsm_system_id}
            </Badge>
            <Badge
              variant={currentApp.cmdb_criticality === "TIER_1" ? "destructive" : "secondary"}
              className="text-[10px] font-mono"
            >
              {currentApp.cmdb_criticality}
            </Badge>
          </div>

          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1 flex-wrap">
            <span className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" />
              Owner: <strong className="text-foreground font-medium">{currentApp.app_owner_name || "Unassigned"}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" />
              Governed Datasets: <strong className="text-foreground font-medium">{currentApp.datasets_count}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <ArrowRightLeft className="w-3.5 h-3.5" />
              System Integrations: <strong className="text-foreground font-medium">{currentApp.integrations_count}</strong>
            </span>
            <span className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full font-mono">
              <ExternalLink className="w-3 h-3" />
              Mastered in ServiceNow CMDB
            </span>
          </div>
        </div>
      </div>

      {/* Application Switcher Combobox */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Active System:
        </span>
        <Select
          value={currentApp.asset_head_id}
          onValueChange={(val) => setSelectedAppHeadId(val)}
        >
          <SelectTrigger className="w-[280px] h-9 text-xs bg-background">
            <SelectValue placeholder="Switch Application..." />
          </SelectTrigger>
          <SelectContent>
            {applications.map((app) => (
              <SelectItem key={app.asset_head_id} value={app.asset_head_id} className="text-xs">
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="font-medium truncate">{app.itsm_system_name}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">({app.itsm_system_id})</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
};
