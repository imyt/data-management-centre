import React, { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckSquare,
  ArrowRight,
  TrendingUp,
  FileQuestion,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  Loader2,
  Sliders,
} from "lucide-react";
import { complianceApi } from "../api/compliance.api";
import { useRemediationUiStore } from "../stores/remediation.store";
import type { IComplianceIssue } from "../types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const RemediationHub: React.FC = () => {
  const queryClient = useQueryClient();
  const [remediatingId, setRemediatingId] = useState<string | null>(null);

  const {
    severityFilter,
    statusFilter,
    lastScanMessage,
    setSeverityFilter,
    setStatusFilter,
    setLastScanMessage,
  } = useRemediationUiStore();

  // Query filtered issues for ledger table
  const {
    data: issues = [],
    isLoading,
  } = useQuery({
    queryKey: ["compliance-issues", severityFilter, statusFilter],
    queryFn: () =>
      complianceApi.getIssues({
        severity: severityFilter !== "ALL" ? severityFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      }),
  });

  // Query overall issues for top KPI summary cards
  const { data: allIssues = [] } = useQuery({
    queryKey: ["compliance-issues-summary"],
    queryFn: () => complianceApi.getIssues(),
  });

  // Automated DQ Scan mutation with live cache invalidation
  const scanMutation = useMutation({
    mutationFn: () => complianceApi.runScan(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["compliance-issues"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-issues-summary"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setLastScanMessage(
        `Scanned ${data.scanned_assets_count} assets at ${timeStr}: ${data.new_issues_created_count} new, ${data.existing_issues_count} existing.`
      );
    },
  });

  // One-Click Fix / Remediate mutation with live cache invalidation
  const remediateMutation = useMutation({
    mutationFn: (issueId: string) => complianceApi.remediateIssue(issueId, { auto_apply_fix: true }),
    onMutate: (issueId) => {
      setRemediatingId(issueId);
    },
    onSettled: () => {
      setRemediatingId(null);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-issues"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-issues-summary"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  // KPI calculations from global issues state
  const openIssues = allIssues.filter((i) => i.status !== "RESOLVED");
  const resolvedIssues = allIssues.filter((i) => i.status === "RESOLVED");
  const criticalHighCount = openIssues.filter(
    (i) => i.severity === "CRITICAL" || i.severity === "HIGH"
  ).length;
  const piiIssueCount = openIssues.filter((i) =>
    i.title.toLowerCase().includes("pii")
  ).length;
  const thinDescCount = openIssues.filter((i) =>
    i.title.toLowerCase().includes("description")
  ).length;

  const totalCalculated = allIssues.length;
  const velocityPercentage =
    totalCalculated > 0
      ? ((resolvedIssues.length / totalCalculated) * 100).toFixed(1)
      : "100";

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Header */}
      <div className="h-14 border-b border-border bg-card px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
            <CheckSquare className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground">Self-Service Remediation Hub</h1>
            <p className="text-[11px] text-muted-foreground">
              Automated anomaly scans, policy breach reconciliations, and one-click corrective workflows.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {lastScanMessage ? (
            <span className="text-[11px] text-muted-foreground font-mono hidden md:inline-block">
              {lastScanMessage}
            </span>
          ) : (
            <span className="text-[11px] text-muted-foreground font-mono hidden md:inline-block">
              Automated DQ Scan: Ready
            </span>
          )}

          <Link
            to="/policies"
            className="flex items-center space-x-1 px-2.5 py-1.5 bg-muted hover:bg-muted/80 text-foreground border border-border rounded-md text-xs font-medium transition-all shadow-xs"
          >
            <Sliders className="w-3.5 h-3.5 text-primary" />
            <span>Manage Policy Rules</span>
          </Link>

          <button
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 rounded-md text-xs font-medium transition-all shadow-xs cursor-pointer"
          >
            {scanMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running Scan...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Run Automated DQ Scan</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto p-4 max-w-6xl w-full mx-auto space-y-4">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-card border border-border rounded-lg shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                Policy Breaches
              </span>
              <AlertTriangle className="w-3.5 h-3.5 text-destructive" />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-xl font-bold text-destructive font-mono">
                {criticalHighCount}
              </span>
              <span className="text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded font-medium">
                High / Critical
              </span>
            </div>
          </div>

          <div className="p-3 bg-card border border-border rounded-lg shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                Unclassified PII
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-amber-500" />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-xl font-bold text-amber-500 font-mono">
                {piiIssueCount}
              </span>
              <span className="text-[10px] text-amber-600 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded font-medium">
                Pending Attestation
              </span>
            </div>
          </div>

          <div className="p-3 bg-card border border-border rounded-lg shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                Thin Definitions
              </span>
              <FileQuestion className="w-3.5 h-3.5 text-sky-500" />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-xl font-bold text-sky-500 font-mono">
                {thinDescCount}
              </span>
              <span className="text-[10px] text-sky-600 dark:text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded font-medium">
                Catalog Health
              </span>
            </div>
          </div>

          <div className="p-3 bg-card border border-border rounded-lg shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                Remediation Velocity
              </span>
              <TrendingUp className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-xl font-bold text-primary font-mono">
                {velocityPercentage}%
              </span>
              <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded flex items-center gap-0.5 font-medium">
                {resolvedIssues.length} Resolved
              </span>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-card border border-border p-2.5 rounded-lg text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Severity:
            </span>
            {(["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                  severityFilter === sev
                    ? "bg-primary text-primary-foreground shadow-2xs"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Status:
            </span>
            {(["ALL", "OPEN", "RESOLVED"] as const).map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                  statusFilter === st
                    ? "bg-primary text-primary-foreground shadow-2xs"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Issue Ledger Table */}
        <div className="border border-border rounded-lg bg-card overflow-hidden shadow-2xs">
          <div className="grid grid-cols-12 gap-2 px-3 py-2.5 bg-muted/40 border-b border-border text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            <span className="col-span-4">Non-Compliant Asset</span>
            <span className="col-span-4">Detected Governance Anomaly</span>
            <span className="col-span-2">Severity</span>
            <span className="col-span-2 text-right">Actions</span>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground flex flex-col items-center justify-center space-y-2">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
              <p className="text-xs">Loading live compliance issues...</p>
            </div>
          ) : issues.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground flex flex-col items-center justify-center space-y-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-500" />
              <div>
                <p className="text-xs font-semibold text-foreground">
                  No issues found matching criteria
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  All monitored assets comply with policy rules, or no scan has been executed yet.
                </p>
              </div>
              <button
                onClick={() => scanMutation.mutate()}
                disabled={scanMutation.isPending}
                className="mt-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 transition-colors shadow-2xs cursor-pointer"
              >
                Trigger Automated DQ Scan
              </button>
            </div>
          ) : (
            <div className="divide-y divide-border/60">
              {issues.map((item: IComplianceIssue) => {
                const isResolving = remediatingId === item.id;
                const isResolved = item.status === "RESOLVED";

                return (
                  <div
                    key={item.id}
                    className={`grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-accent/40 transition-colors text-xs ${
                      isResolved ? "opacity-60 bg-muted/20" : ""
                    }`}
                  >
                    {/* Asset Name & Link */}
                    <div className="col-span-4 flex items-center space-x-2">
                      <FileQuestion className="w-4 h-4 text-muted-foreground shrink-0" />
                      <div className="truncate">
                        <span className="font-semibold text-foreground truncate block">
                          {item.asset_name || "Enterprise Asset"}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-mono block truncate">
                          ID: {item.target_asset_head_id.substring(0, 8)}...
                        </span>
                      </div>
                    </div>

                    {/* Anomaly / Title & Description */}
                    <div className="col-span-4 text-muted-foreground text-[11px] pr-2">
                      <div className="font-medium text-foreground truncate">{item.title}</div>
                      <div className="text-[10px] text-muted-foreground truncate" title={item.description}>
                        {item.description}
                      </div>
                    </div>

                    {/* Severity Badge */}
                    <div className="col-span-2">
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          item.severity === "CRITICAL"
                            ? "bg-destructive/10 text-destructive border border-destructive/20"
                            : item.severity === "HIGH"
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                            : item.severity === "MEDIUM"
                            ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20"
                            : "bg-muted text-muted-foreground border border-border"
                        }`}
                      >
                        {item.severity}
                      </span>
                      {isResolved && (
                        <span className="ml-1.5 text-[9px] text-emerald-600 dark:text-emerald-400 font-mono">
                          RESOLVED
                        </span>
                      )}
                    </div>

                    {/* Action Buttons: Remediate / Fix & Catalog Inspect */}
                    <div className="col-span-2 flex items-center justify-end space-x-1.5">
                      {!isResolved ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() => remediateMutation.mutate(item.id)}
                            disabled={isResolving}
                            title="Auto-apply compliance fix to asset"
                            className="h-6 text-[11px] px-2 font-medium gap-1 shadow-2xs"
                          >
                            {isResolving ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Sparkles className="w-3 h-3" />
                            )}
                            <span>Fix</span>
                          </Button>

                          <Link
                            to="/catalog"
                            search={{ assetId: item.target_asset_head_id }}
                            className="flex items-center space-x-0.5 px-2 py-1 bg-muted hover:bg-muted/80 text-foreground rounded text-[11px] font-medium transition-colors border border-border shadow-2xs"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        </>
                      ) : (
                        <Badge variant="soft" className="font-mono text-[10px] gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                          <span>Remediated</span>
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
