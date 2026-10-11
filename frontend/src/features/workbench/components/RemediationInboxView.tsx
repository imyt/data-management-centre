import React from "react";
import { Clock, CheckCircle2, ArrowRight, Shield, Database, ArrowRightLeft, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useWorkbenchUiStore, type RemediationModalType } from "../stores/workbench.store";
import type { WorkbenchIssue } from "../types";

interface RemediationInboxViewProps {
  issues: WorkbenchIssue[];
  isLoading?: boolean;
}

export const RemediationInboxView: React.FC<RemediationInboxViewProps> = ({
  issues,
  isLoading,
}) => {
  const { urgencyFilter, openRemediationModal } = useWorkbenchUiStore();

  const filteredIssues = React.useMemo(() => {
    return issues.filter((issue) => {
      if (urgencyFilter === "CRITICAL") return issue.severity === "CRITICAL";
      if (urgencyFilter === "HIGH") return issue.severity === "HIGH";
      if (urgencyFilter === "BREACHING_SOON") return issue.seconds_remaining <= 172800 && issue.status !== "RESOLVED";
      if (urgencyFilter === "WAIVERS") return issue.status === "EXCEPTION_GRANTED";
      return true;
    });
  }, [issues, urgencyFilter]);

  const formatCountdown = (seconds: number) => {
    if (seconds <= 0) return "SLA Breached!";
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    if (days > 0) return `${days}d ${hours}h remaining`;
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m remaining`;
  };

  const getModalTypeForIssue = (ruleCode: string): RemediationModalType => {
    if (ruleCode.startsWith("MOV")) return "INTEGRITY";
    if (ruleCode.startsWith("DRIFT")) return "DRIFT";
    if (ruleCode.startsWith("STOR")) return "PURGE";
    if (ruleCode.startsWith("PRIV")) return "MASKING";
    return "INTEGRITY";
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-muted/30 border border-border rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (filteredIssues.length === 0) {
    return (
      <Card className="border-dashed py-12 text-center bg-card">
        <CardContent className="space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/20">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-foreground">Zero Compliance Debt</h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            All data movement integrity patterns, storage retention cycles, and column privacy controls are certified. SLA timers are stopped.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span>
          Showing <strong className="text-foreground">{filteredIssues.length}</strong> actionable compliance defects requiring application owner remediation
        </span>
        <span className="text-[11px] font-mono">Sorted by Urgent SLA Countdown</span>
      </div>

      <div className="space-y-3">
        {filteredIssues.map((issue) => {
          const isResolved = issue.status === "RESOLVED";
          const isExempt = issue.status === "EXCEPTION_GRANTED";
          const isBreachingSoon = issue.seconds_remaining > 0 && issue.seconds_remaining <= 172800;
          const isBreached = issue.seconds_remaining <= 0 && !isResolved;

          return (
            <div
              key={issue.id}
              className={`bg-card border rounded-xl p-5 shadow-xs transition-all hover:border-primary/40 ${
                isResolved
                  ? "opacity-60 border-border"
                  : isBreached
                  ? "border-red-500/40 bg-red-500/5"
                  : isBreachingSoon
                  ? "border-amber-500/40 bg-amber-500/5"
                  : "border-border"
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                {/* Defect Details */}
                <div className="space-y-2.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="font-mono text-xs font-bold bg-muted/80 text-foreground">
                      {issue.rule_code || "DEFECT"}
                    </Badge>

                    <Badge
                      variant={
                        issue.severity === "CRITICAL"
                          ? "destructive"
                          : issue.severity === "HIGH"
                          ? "destructive"
                          : "secondary"
                      }
                      className="text-[10px] font-mono font-bold"
                    >
                      {issue.severity}
                    </Badge>

                    {/* SLA Countdown Badge */}
                    {!isResolved && !isExempt && (
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold border ${
                          isBreached
                            ? "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30"
                            : isBreachingSoon
                            ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30 animate-pulse"
                            : "bg-muted text-muted-foreground border-border"
                        }`}
                      >
                        <Clock className="w-3.5 h-3.5" />
                        {formatCountdown(issue.seconds_remaining)}
                      </span>
                    )}

                    {isExempt && (
                      <Badge variant="soft" className="text-[10px] font-mono">
                        Waiver Active (SLA Paused)
                      </Badge>
                    )}

                    {isResolved && (
                      <Badge variant="outline" className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                        Resolved
                      </Badge>
                    )}
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-foreground tracking-tight">{issue.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{issue.description}</p>
                  </div>

                  {/* Technical Entity Context Box */}
                  <div className="flex items-center gap-3 text-xs bg-muted/40 p-2.5 rounded-lg border border-border/60 flex-wrap">
                    {issue.integration && (
                      <span className="flex items-center gap-1.5 font-medium text-foreground">
                        <ArrowRightLeft className="w-3.5 h-3.5 text-primary" />
                        Integration: <span className="font-mono text-primary">{issue.integration.itsm_integration_id}</span> ({issue.integration.transfer_type})
                      </span>
                    )}

                    {issue.storage_control && (
                      <span className="flex items-center gap-1.5 font-medium text-foreground">
                        <Database className="w-3.5 h-3.5 text-primary" />
                        Storage: <span className="font-mono text-primary">{issue.storage_control.storage_name}</span> ({issue.storage_control.retention_period_days}d Retention)
                      </span>
                    )}

                    {issue.physical_column && (
                      <span className="flex items-center gap-1.5 font-medium text-foreground">
                        <Shield className="w-3.5 h-3.5 text-primary" />
                        Column: <span className="font-mono text-primary">{issue.physical_column.column_name}</span> ({issue.physical_column.table_name || "Physical Table"})
                      </span>
                    )}

                    {issue.exemption && (
                      <span className="flex items-center gap-1.5 text-primary">
                        <FileText className="w-3.5 h-3.5" />
                        Compensating Control: <span className="italic">{issue.exemption.compensating_controls}</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Remediation Action Controls */}
                {!isResolved && (
                  <div className="flex flex-row lg:flex-col items-center lg:items-end gap-2 shrink-0 pt-2 lg:pt-0">
                    <Button
                      size="sm"
                      onClick={() => openRemediationModal(issue, getModalTypeForIssue(issue.rule_code))}
                      className="text-xs h-8 px-4 font-bold gap-1.5 shadow-xs"
                    >
                      <span>Remediate Now</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Button>

                    {!isExempt && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openRemediationModal(issue, "EXEMPTION")}
                        className="text-xs h-8 px-3 text-muted-foreground hover:text-foreground"
                      >
                        Request Waiver
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
