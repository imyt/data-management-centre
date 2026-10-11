import React from "react";
import { ShieldAlert, Clock, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useWorkbenchUiStore } from "../stores/workbench.store";
import type { WorkbenchSummary } from "../types";

interface ExecutivePostureBannerProps {
  summary?: WorkbenchSummary;
}

export const ExecutivePostureBanner: React.FC<ExecutivePostureBannerProps> = ({ summary }) => {
  const { urgencyFilter, setUrgencyFilter, setActiveTab } = useWorkbenchUiStore();

  const posture = summary?.posture || {
    health_score: 100,
    total_defects: 0,
    open_defects: 0,
    resolved_defects: 0,
    active_exemptions: 0,
    breached_defects: 0,
    breaching_soon_defects: 0,
  };

  const getHealthColor = (score: number) => {
    if (score >= 90) return "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
    if (score >= 70) return "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/30";
    return "text-red-600 dark:text-red-400 bg-red-500/10 border-red-500/30";
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
        {/* Metric 1: Overall Health Score */}
        <div className="flex items-center gap-3.5 p-3 rounded-lg bg-muted/40 border border-border/80">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold font-mono text-lg border ${getHealthColor(
              posture.health_score
            )}`}
          >
            {posture.health_score}%
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Governance Posture</div>
            <div className="text-sm font-bold text-foreground">
              {posture.health_score >= 90
                ? "Fully Certified"
                : posture.health_score >= 70
                ? "Needs Remediation"
                : "Critical Compliance Risk"}
            </div>
          </div>
        </div>

        {/* Metric 2: Open Actionable Defects */}
        <div className="flex items-center gap-3.5 p-3 rounded-lg bg-muted/40 border border-border/80">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Actionable Defects</div>
            <div className="text-sm font-bold text-foreground flex items-center gap-1.5">
              <span>{posture.open_defects} Open</span>
              {posture.open_defects > 0 && (
                <Badge variant="outline" className="text-[10px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30">
                  Requires Fix
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Metric 3: Urgent SLA Timers */}
        <div className="flex items-center gap-3.5 p-3 rounded-lg bg-muted/40 border border-border/80">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
            posture.breached_defects > 0 || posture.breaching_soon_defects > 0
              ? "bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400"
              : "bg-muted border border-border text-muted-foreground"
          }`}>
            <Clock className={`w-5 h-5 ${posture.breaching_soon_defects > 0 ? "animate-pulse" : ""}`} />
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">SLA Deadlines</div>
            <div className="text-sm font-bold text-foreground">
              {posture.breached_defects > 0 ? (
                <span className="text-red-600 dark:text-red-400">{posture.breached_defects} Breached!</span>
              ) : posture.breaching_soon_defects > 0 ? (
                <span className="text-amber-600 dark:text-amber-400">{posture.breaching_soon_defects} &lt; 48h Remaining</span>
              ) : (
                <span className="text-muted-foreground font-normal">All SLAs Healthy</span>
              )}
            </div>
          </div>
        </div>

        {/* Metric 4: Approved Exemptions / Resolved */}
        <div className="flex items-center gap-3.5 p-3 rounded-lg bg-muted/40 border border-border/80">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Resolved This Quarter</div>
            <div className="text-sm font-bold text-foreground flex items-center gap-2">
              <span>{posture.resolved_defects} Cleared</span>
              {posture.active_exemptions > 0 && (
                <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
                  {posture.active_exemptions} Waivers
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SLA Triage Filter Bar */}
      <div className="flex items-center justify-between border-t border-border/60 pt-3 flex-wrap gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-muted-foreground font-medium mr-1">Triage Filter:</span>
          {(
            [
              { id: "ALL", label: "All Defects", count: posture.open_defects },
              { id: "CRITICAL", label: "Critical", count: summary?.urgent_defects.filter((d) => d.severity === "CRITICAL").length || 0 },
              { id: "BREACHING_SOON", label: "Breaching Soon (< 48h)", count: posture.breaching_soon_defects },
              { id: "WAIVERS", label: "Active Waivers", count: posture.active_exemptions },
            ] as const
          ).map((filter) => (
            <Button
              key={filter.id}
              variant={urgencyFilter === filter.id ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setUrgencyFilter(filter.id);
                setActiveTab("inbox");
              }}
              className="h-7 text-xs px-2.5 rounded-md font-medium"
            >
              {filter.label}
              <Badge
                variant={urgencyFilter === filter.id ? "secondary" : "outline"}
                className="ml-1.5 px-1.5 py-0 text-[10px] font-mono"
              >
                {filter.count}
              </Badge>
            </Button>
          ))}
        </div>

        <div className="text-[11px] text-muted-foreground">
          SLA Policy: <span className="font-medium text-foreground">14-Day Mandatory Self-Service Resolution</span>
        </div>
      </div>
    </div>
  );
};
