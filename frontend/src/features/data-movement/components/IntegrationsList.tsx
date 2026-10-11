import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  ArrowRight,
  ArrowLeft,
  Database,
  Plus,
  Trash2,
  Shield,
  ShieldCheck,
  Clock,
  Send,
  CheckCircle,
  AlertTriangle,
  Search,
  ChevronDown,
  ChevronRight,
  LayoutList,
  LayoutGrid,
  ChevronLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  listApplicationIntegrationsOptions,
  unbindScopeMutation,
  submitCertificationMutation,
} from "@/api/client";
import type { ApplicationIntegrationRead } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";
import { GovernanceStatusBadge } from "./GovernanceStatusBadge";
import { IsrBadge } from "./IsrBadge";

export const IntegrationsList: React.FC = () => {
  const {
    selectedAppHeadId,
    setBindingIntegrationId,
    setDeclaringPatternIntegrationId,
    setVerifyingIntegrationId,
    integrationStatusFilter,
    setIntegrationStatusFilter,
    integrationDirectionFilter,
    setIntegrationDirectionFilter,
    integrationTransferTypeFilter,
    setIntegrationTransferTypeFilter,
    integrationViewMode,
    setIntegrationViewMode,
    integrationPage,
    setIntegrationPage,
    integrationPageSize,
    setIntegrationPageSize,
    expandedIntegrationIds,
    toggleExpandIntegration,
    expandAllIntegrations,
    collapseAllIntegrations,
  } = useDataMovementUiStore();

  const queryClient = useQueryClient();
  const [searchFilter, setSearchFilter] = React.useState("");
  const [actionError, setActionError] = React.useState<{ id: string; message: string } | null>(null);
  const [unbindingTarget, setUnbindingTarget] = React.useState<{
    integrationId: string;
    datasetId: string;
    datasetName: string;
    integrationCode: string;
  } | null>(null);

  const { data: integrations = [], isLoading } = useQuery({
    ...listApplicationIntegrationsOptions({
      path: { app_head_id: selectedAppHeadId || "" },
    }),
    enabled: Boolean(selectedAppHeadId),
  });

  const unbindMutation = useMutation({
    ...unbindScopeMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setUnbindingTarget(null);
    },
    onError: (err: any, variables: any) => {
      setActionError({
        id: variables.path.integration_id,
        message: err?.body?.detail || err?.message || "Failed to remove dataset binding.",
      });
      setUnbindingTarget(null);
    },
  });

  const submitCertificationMut = useMutation({
    ...submitCertificationMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setActionError(null);
    },
    onError: (err: any, variables: any) => {
      setActionError({
        id: variables.path.integration_id,
        message: err?.body?.detail || err?.message || "Failed to submit certification.",
      });
    },
  });

  const confirmUnbind = () => {
    if (!unbindingTarget) return;
    unbindMutation.mutate({
      path: {
        integration_id: unbindingTarget.integrationId,
        dataset_id: unbindingTarget.datasetId,
      },
    });
  };

  const handleSubmitCertification = (integration: ApplicationIntegrationRead) => {
    setActionError(null);
    submitCertificationMut.mutate({
      path: { integration_id: integration.id },
      body: {
        certification_notes: `Attestation submitted by Application Owner for ${integration.itsm_integration_id}. Certified transfer pattern configured.`,
      },
    });
  };

  // High-performance client-side filtering across hundreds of items
  const filteredIntegrations = React.useMemo(() => {
    return integrations.filter((item) => {
      // Text Search
      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        const matchesCode = item.itsm_integration_id.toLowerCase().includes(q);
        const matchesSource = (item.source_app_name || "").toLowerCase().includes(q);
        const matchesTarget = (item.target_app_name || "").toLowerCase().includes(q);
        const matchesPattern = (item.integrity_pattern || "").toLowerCase().includes(q);
        const matchesDatasets = item.bound_datasets?.some((d) =>
          (d.dataset_name || "").toLowerCase().includes(q)
        );
        if (!matchesCode && !matchesSource && !matchesTarget && !matchesPattern && !matchesDatasets) {
          return false;
        }
      }

      // Status Filter
      if (integrationStatusFilter !== "ALL" && item.governance_status !== integrationStatusFilter) {
        return false;
      }

      // Direction Filter
      if (integrationDirectionFilter !== "ALL" && item.direction !== integrationDirectionFilter) {
        return false;
      }

      // Transfer Type Filter
      if (
        integrationTransferTypeFilter !== "ALL" &&
        item.transfer_type !== integrationTransferTypeFilter
      ) {
        return false;
      }

      return true;
    });
  }, [
    integrations,
    searchFilter,
    integrationStatusFilter,
    integrationDirectionFilter,
    integrationTransferTypeFilter,
  ]);

  // Pagination calculation
  const totalItems = filteredIntegrations.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / integrationPageSize));
  const currentPage = Math.min(integrationPage, totalPages);
  const startIndex = (currentPage - 1) * integrationPageSize;
  const paginatedIntegrations = filteredIntegrations.slice(
    startIndex,
    startIndex + integrationPageSize
  );

  // Status statistics for quick KPIs
  const stats = React.useMemo(() => {
    const total = integrations.length;
    const compliant = integrations.filter((i) => i.governance_status === "COMPLIANT").length;
    const pending = integrations.filter((i) => i.governance_status === "PENDING_VERIFICATION").length;
    const remediation = integrations.filter((i) => i.governance_status === "IN_REMEDIATION").length;
    const ungoverned = integrations.filter((i) => i.governance_status === "UNGOVERNED").length;
    const breached = integrations.filter((i) => i.sla_breached).length;
    return { total, compliant, pending, remediation, ungoverned, breached };
  }, [integrations]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="h-14 bg-muted/40 border border-border rounded-lg animate-pulse" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-16 bg-muted/20 border border-border rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. Metric KPI Bar for Fast Triaging */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
        <button
          type="button"
          onClick={() => setIntegrationStatusFilter("ALL")}
          className={`p-2.5 rounded-lg border text-left transition-all ${
            integrationStatusFilter === "ALL"
              ? "border-primary bg-primary/5 font-semibold"
              : "border-border bg-card hover:bg-muted/30"
          }`}
        >
          <div className="text-[11px] text-muted-foreground">Total Integrations</div>
          <div className="text-lg font-bold text-foreground mt-0.5">{stats.total}</div>
        </button>

        <button
          type="button"
          onClick={() => setIntegrationStatusFilter("COMPLIANT")}
          className={`p-2.5 rounded-lg border text-left transition-all ${
            integrationStatusFilter === "COMPLIANT"
              ? "border-emerald-500 bg-emerald-500/10 font-semibold"
              : "border-border bg-card hover:bg-muted/30"
          }`}
        >
          <div className="text-[11px] text-emerald-600 dark:text-emerald-400">Compliant</div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
            {stats.compliant}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setIntegrationStatusFilter("PENDING_VERIFICATION")}
          className={`p-2.5 rounded-lg border text-left transition-all ${
            integrationStatusFilter === "PENDING_VERIFICATION"
              ? "border-primary bg-primary/10 font-semibold"
              : "border-border bg-card hover:bg-muted/30"
          }`}
        >
          <div className="text-[11px] text-primary">Verification Pending</div>
          <div className="text-lg font-bold text-primary mt-0.5">
            {stats.pending}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setIntegrationStatusFilter("IN_REMEDIATION")}
          className={`p-2.5 rounded-lg border text-left transition-all ${
            integrationStatusFilter === "IN_REMEDIATION"
              ? "border-amber-500 bg-amber-500/10 font-semibold"
              : "border-border bg-card hover:bg-muted/30"
          }`}
        >
          <div className="text-[11px] text-amber-600 dark:text-amber-400">In Remediation</div>
          <div className="text-lg font-bold text-amber-600 dark:text-amber-400 mt-0.5">
            {stats.remediation}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setIntegrationStatusFilter("UNGOVERNED")}
          className={`p-2.5 rounded-lg border text-left transition-all ${
            integrationStatusFilter === "UNGOVERNED"
              ? "border-rose-500 bg-rose-500/10 font-semibold"
              : "border-border bg-card hover:bg-muted/30"
          }`}
        >
          <div className="text-[11px] text-rose-600 dark:text-rose-400">Ungoverned</div>
          <div className="text-lg font-bold text-rose-600 dark:text-rose-400 mt-0.5">
            {stats.ungoverned}
          </div>
        </button>

        <div className="p-2.5 rounded-lg border border-border bg-card">
          <div className="text-[11px] text-muted-foreground">SLA Breached</div>
          <div
            className={`text-lg font-bold mt-0.5 ${
              stats.breached > 0 ? "text-destructive" : "text-muted-foreground"
            }`}
          >
            {stats.breached}
          </div>
        </div>
      </div>

      {/* 2. Compact Control Bar (Search, Direction, Type, Density, Batch Expansion) */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
            <Input
              placeholder="Filter by ID, partner app, pattern, or dataset..."
              value={searchFilter}
              onChange={(e) => {
                setSearchFilter(e.target.value);
                setIntegrationPage(1);
              }}
              className="pl-8 h-8 text-xs bg-background"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Direction Filter */}
          <Select
            value={integrationDirectionFilter}
            onValueChange={setIntegrationDirectionFilter}
          >
            <SelectTrigger className="h-8 text-xs w-32 bg-background">
              <SelectValue placeholder="Direction" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL" className="text-xs">All Directions</SelectItem>
              <SelectItem value="INBOUND" className="text-xs">Inbound</SelectItem>
              <SelectItem value="OUTBOUND" className="text-xs">Outbound</SelectItem>
            </SelectContent>
          </Select>

          {/* Transfer Type Filter */}
          <Select
            value={integrationTransferTypeFilter}
            onValueChange={setIntegrationTransferTypeFilter}
          >
            <SelectTrigger className="h-8 text-xs w-36 bg-background">
              <SelectValue placeholder="Protocol" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL" className="text-xs">All Protocols</SelectItem>
              <SelectItem value="REST_API" className="text-xs">REST API</SelectItem>
              <SelectItem value="EVENT_STREAM_KAFKA" className="text-xs">Kafka Event Stream</SelectItem>
              <SelectItem value="BATCH_ETL" className="text-xs">Batch ETL</SelectItem>
              <SelectItem value="CDC_STREAMING" className="text-xs">CDC Streaming</SelectItem>
              <SelectItem value="SFTP_FILE" className="text-xs">SFTP File</SelectItem>
              <SelectItem value="DIRECT_DB_LINK" className="text-xs">Direct DB Link</SelectItem>
              <SelectItem value="MESSAGE_QUEUE_MQ" className="text-xs">Message Queue MQ</SelectItem>
            </SelectContent>
          </Select>

          {/* View Density Toggle */}
          <div className="flex items-center border border-border rounded-md bg-muted/40 p-0.5">
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 ${
                integrationViewMode === "compact"
                  ? "bg-background text-foreground shadow-2xs"
                  : "text-muted-foreground"
              }`}
              onClick={() => setIntegrationViewMode("compact")}
              title="Compact Table / Tree View"
            >
              <LayoutList className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 ${
                integrationViewMode === "card"
                  ? "bg-background text-foreground shadow-2xs"
                  : "text-muted-foreground"
              }`}
              onClick={() => setIntegrationViewMode("card")}
              title="Expanded Cards View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </Button>
          </div>

          {/* Batch Expand / Collapse for Dense View */}
          {integrationViewMode === "compact" && (
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-[11px] px-2 shadow-2xs"
                onClick={() =>
                  expandAllIntegrations(paginatedIntegrations.map((i) => i.id))
                }
              >
                Expand All
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-[11px] px-2 shadow-2xs"
                onClick={collapseAllIntegrations}
              >
                Collapse
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Global Error Banner if any action failed */}
      {actionError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-xs text-destructive flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{actionError.message}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActionError(null)}
            className="h-6 text-[10px] px-2 text-destructive hover:bg-destructive/10"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* 3. Empty State */}
      {filteredIntegrations.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-xl p-12 text-center">
          <ArrowRightLeft className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-foreground">No Matching Integrations</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            {integrations.length === 0
              ? "No directional integrations synchronized from ITSM for this application."
              : "No integrations match current search filters. Try clearing the filter parameters."}
          </p>
          {integrations.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="mt-3 text-xs"
              onClick={() => {
                setSearchFilter("");
                setIntegrationStatusFilter("ALL");
                setIntegrationDirectionFilter("ALL");
                setIntegrationTransferTypeFilter("ALL");
              }}
            >
              Reset Filters
            </Button>
          )}
        </div>
      ) : integrationViewMode === "compact" ? (
        /* 4A. High-Density Compact Table View with Expandable Row Detail */
        <div className="border border-border rounded-xl overflow-hidden bg-card shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="py-2.5 px-3 w-8"></th>
                  <th className="py-2.5 px-3">Integration CI</th>
                  <th className="py-2.5 px-3">Flow Direction & Partner</th>
                  <th className="py-2.5 px-3">Protocol / Freq</th>
                  <th className="py-2.5 px-3">Bound Datasets</th>
                  <th className="py-2.5 px-3">Integrity Pattern</th>
                  <th className="py-2.5 px-3">SLA / Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {paginatedIntegrations.map((integ) => {
                  const isExpanded = expandedIntegrationIds.includes(integ.id);
                  const isPendingVerification = integ.governance_status === "PENDING_VERIFICATION";
                  const isInRemediation = integ.governance_status === "IN_REMEDIATION";
                  const isUngoverned = integ.governance_status === "UNGOVERNED";

                  const boundCount = integ.bound_datasets?.length || 0;
                  const hasPattern =
                    integ.integrity_pattern && integ.integrity_pattern !== "NONE_UNENFORCED";
                  const canSubmitCertification =
                    (isUngoverned || isInRemediation) && boundCount > 0 && hasPattern;

                  return (
                    <React.Fragment key={integ.id}>
                      <tr
                        className={`hover:bg-muted/30 transition-colors ${
                          integ.sla_breached ? "bg-destructive/[0.03]" : ""
                        }`}
                      >
                        {/* Expand toggle */}
                        <td className="py-2.5 px-3">
                          <button
                            type="button"
                            onClick={() => toggleExpandIntegration(integ.id)}
                            className="text-muted-foreground hover:text-foreground p-0.5 rounded"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>

                        {/* Integration Code */}
                        <td className="py-2.5 px-3 font-mono font-bold text-foreground whitespace-nowrap">
                          <Badge variant="outline" className="font-mono text-[11px] bg-background">
                            {integ.itsm_integration_id}
                          </Badge>
                        </td>

                        {/* Direction & System Name */}
                        <td className="py-2.5 px-3 max-w-xs">
                          <div className="flex items-center gap-1.5 font-medium text-foreground">
                            {integ.direction === "OUTBOUND" ? (
                              <ArrowRight className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                            ) : (
                              <ArrowLeft className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                            )}
                            <span className="truncate">
                              {integ.direction === "OUTBOUND"
                                ? integ.target_app_name || "Target App"
                                : integ.source_app_name || "Source App"}
                            </span>
                          </div>
                        </td>

                        {/* Protocol & Frequency */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex items-center gap-1">
                            <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0">
                              {integ.transfer_type}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground">
                              {integ.frequency}
                            </span>
                          </div>
                        </td>

                        {/* Bound Datasets summary */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <Badge
                              variant={boundCount > 0 ? "outline" : "destructive"}
                              className="text-[10px] font-mono"
                            >
                              {boundCount} Dataset{boundCount !== 1 ? "s" : ""}
                            </Badge>
                            {boundCount === 0 && (
                              <span className="text-[10px] text-destructive font-medium">
                                Missing
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Transfer Integrity Pattern */}
                        <td className="py-2.5 px-3 max-w-xs truncate">
                          {hasPattern ? (
                            <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                              <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                              <span className="truncate text-[11px]">
                                {integ.integrity_pattern.replace(/_/g, " ")}
                              </span>
                            </div>
                          ) : (
                            <span className="text-[11px] text-amber-600 dark:text-amber-400 italic">
                              Undeclared
                            </span>
                          )}
                        </td>

                        {/* Status & SLA */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <GovernanceStatusBadge status={integ.governance_status} />
                            {integ.sla_days_remaining !== null &&
                              integ.sla_days_remaining !== undefined && (
                                <span
                                  className={`text-[10px] font-mono font-medium ${
                                    integ.sla_breached
                                      ? "text-destructive font-bold"
                                      : integ.sla_days_remaining <= 3
                                      ? "text-amber-600 dark:text-amber-400"
                                      : "text-muted-foreground"
                                  }`}
                                >
                                  {integ.sla_breached
                                    ? "BREACHED"
                                    : `${integ.sla_days_remaining}d SLA`}
                                </span>
                              )}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-xs"
                              onClick={() => setBindingIntegrationId(integ.id)}
                            >
                              <Plus className="w-3 h-3 mr-1" />
                              Bind
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-xs"
                              onClick={() => setDeclaringPatternIntegrationId(integ.id)}
                            >
                              <Shield className="w-3 h-3 mr-1" />
                              Pattern
                            </Button>

                            {canSubmitCertification && (
                              <Button
                                size="sm"
                                className="h-7 px-2.5 text-xs font-semibold gap-1 shadow-2xs"
                                onClick={() => handleSubmitCertification(integ)}
                                disabled={submitCertificationMut.isPending}
                              >
                                <Send className="w-3 h-3" />
                                Submit
                              </Button>
                            )}

                            {isPendingVerification && (
                              <Button
                                size="sm"
                                className="h-7 px-2.5 text-xs font-semibold gap-1 shadow-2xs"
                                onClick={() => setVerifyingIntegrationId(integ.id)}
                              >
                                <ShieldCheck className="w-3 h-3" />
                                Sign-Off
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Details Row: Datasets breakdown and Pattern specifics */}
                      {isExpanded && (
                        <tr className="bg-muted/15 border-b border-border">
                          <td colSpan={8} className="p-4 pl-11">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Left: Datasets list */}
                              <div className="space-y-2">
                                <div className="text-xs font-semibold text-foreground flex items-center justify-between">
                                  <span>Bound Datasets ({boundCount})</span>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-6 text-[10px] px-2 shadow-2xs"
                                    onClick={() => setBindingIntegrationId(integ.id)}
                                  >
                                    <Plus className="w-3 h-3 mr-1" />
                                    Add Dataset
                                  </Button>
                                </div>

                                {boundCount === 0 ? (
                                  <p className="text-xs text-muted-foreground italic">
                                    No datasets associated. Integration requires at least 1 dataset.
                                  </p>
                                ) : (
                                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                    {integ.bound_datasets?.map((b) => (
                                      <div
                                        key={b.id}
                                        className="p-2 rounded border border-border bg-card flex items-center justify-between text-xs"
                                      >
                                        <div className="space-y-0.5">
                                          <div className="flex items-center gap-1.5 flex-wrap">
                                            <span className="font-semibold text-foreground">
                                              {b.dataset_name}
                                            </span>
                                            <IsrBadge
                                              classification={b.isr_classification || "INTERNAL"}
                                            />
                                            {b.encryption_in_transit && (
                                              <Badge
                                                variant="outline"
                                                className="text-[9px] font-mono text-emerald-600 bg-emerald-500/10 border-emerald-500/20"
                                              >
                                                TLS 1.3
                                              </Badge>
                                            )}
                                          </div>
                                          <div className="flex items-center gap-1 flex-wrap text-[10px] text-muted-foreground">
                                            <span>{b.retention_period_days}d retention</span>
                                            {b.data_categories?.map((c) => (
                                              <span key={c} className="bg-muted px-1 rounded font-mono">
                                                {c}
                                              </span>
                                            ))}
                                          </div>
                                        </div>

                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                          onClick={() =>
                                            setUnbindingTarget({
                                              integrationId: integ.id,
                                              datasetId: b.data_set_id,
                                              datasetName: b.dataset_name || "Dataset",
                                              integrationCode: integ.itsm_integration_id,
                                            })
                                          }
                                        >
                                          <Trash2 className="w-3 h-3" />
                                        </Button>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {/* Right: Technical Pattern Specification */}
                              <div className="space-y-2">
                                <div className="text-xs font-semibold text-foreground flex items-center justify-between">
                                  <span>Integrity Transfer Pattern Details</span>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-6 text-[10px] px-2 shadow-2xs"
                                    onClick={() => setDeclaringPatternIntegrationId(integ.id)}
                                  >
                                    Edit Pattern
                                  </Button>
                                </div>

                                <div className="p-2.5 rounded border border-border bg-card text-xs space-y-1">
                                  <div className="font-semibold text-foreground">
                                    {hasPattern
                                      ? integ.integrity_pattern.replace(/_/g, " ")
                                      : "None Declared"}
                                  </div>
                                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                                    {integ.integrity_pattern_details ||
                                      "No technical specifics provided. Declare algorithm and reconciliation mechanisms."}
                                  </p>
                                  {integ.governance_certified_at && (
                                    <div className="text-[10px] text-muted-foreground pt-1 border-t border-border mt-1">
                                      Certified:{" "}
                                      {new Date(integ.governance_certified_at).toLocaleDateString()}
                                      {integ.certified_by_name && ` by ${integ.certified_by_name}`}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* 4B. Detailed Cards View (when user prefers full visual overview) */
        <div className="space-y-4">
          {paginatedIntegrations.map((integ) => {
            const isCompliant = integ.governance_status === "COMPLIANT";
            const isPendingVerification = integ.governance_status === "PENDING_VERIFICATION";
            const isInRemediation = integ.governance_status === "IN_REMEDIATION";
            const isUngoverned = integ.governance_status === "UNGOVERNED";

            const hasBoundDatasets = integ.bound_datasets && integ.bound_datasets.length > 0;
            const hasPattern =
              integ.integrity_pattern && integ.integrity_pattern !== "NONE_UNENFORCED";

            const canSubmitCertification =
              (isUngoverned || isInRemediation) && hasBoundDatasets && hasPattern;

            return (
              <div
                key={integ.id}
                className={`bg-card border rounded-xl overflow-hidden shadow-xs transition-all ${
                  integ.sla_breached
                    ? "border-destructive/60 bg-destructive/[0.02]"
                    : "border-border hover:border-border/80"
                }`}
              >
                {/* Top Bar: ITSM Synchronized Technical Core (Read-Only) */}
                <div className="px-5 py-3 bg-muted/30 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="font-mono text-xs font-bold bg-background text-foreground shadow-2xs"
                      >
                        {integ.itsm_integration_id}
                      </Badge>
                      <span className="text-xs font-semibold text-foreground">
                        {integ.source_app_name || "Source App"}
                      </span>
                      {integ.direction === "OUTBOUND" ? (
                        <ArrowRight className="w-3.5 h-3.5 text-blue-500" />
                      ) : (
                        <ArrowLeft className="w-3.5 h-3.5 text-purple-500" />
                      )}
                      <span className="text-xs font-semibold text-foreground">
                        {integ.target_app_name || "Target App"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                      <Badge variant="secondary" className="text-[10px] font-mono">
                        {integ.direction}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] font-mono bg-background">
                        {integ.transfer_type}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] font-mono bg-background">
                        {integ.frequency}
                      </Badge>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {integ.sla_days_remaining !== null && integ.sla_days_remaining !== undefined && (
                      <div
                        className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md ${
                          integ.sla_breached
                            ? "bg-destructive/15 text-destructive font-bold"
                            : integ.sla_days_remaining <= 3
                            ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 font-bold"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        <Clock className="w-3.5 h-3.5" />
                        <span>
                          {integ.sla_breached
                            ? "SLA Breached"
                            : `${integ.sla_days_remaining}d SLA remaining`}
                        </span>
                      </div>
                    )}

                    <GovernanceStatusBadge status={integ.governance_status} />
                  </div>
                </div>

                {/* Middle Content */}
                <div className="p-5 grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-7 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                        <Database className="w-4 h-4 text-primary" />
                        Bound Governed Datasets ({integ.bound_datasets?.length || 0})
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[11px] gap-1 px-2.5 shadow-2xs"
                        onClick={() => setBindingIntegrationId(integ.id)}
                      >
                        <Plus className="w-3 h-3" />
                        Bind Dataset
                      </Button>
                    </div>

                    {!hasBoundDatasets ? (
                      <div className="p-3.5 rounded-lg border border-dashed border-amber-500/30 bg-amber-500/5 text-xs text-amber-700 dark:text-amber-400 flex items-start gap-2.5">
                        <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
                        <div>
                          <strong className="font-semibold block">Missing Governed Dataset</strong>
                          <p className="text-[11px] mt-0.5">
                            At least one application dataset must be bound before certification.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {integ.bound_datasets?.map((b) => (
                          <div
                            key={b.id}
                            className="p-2.5 rounded-lg border border-border bg-card/60 flex items-center justify-between gap-3 text-xs"
                          >
                            <div className="space-y-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-semibold text-foreground truncate">
                                  {b.dataset_name}
                                </span>
                                <IsrBadge classification={b.isr_classification || "INTERNAL"} />
                                {b.encryption_in_transit && (
                                  <Badge
                                    variant="outline"
                                    className="text-[9px] font-mono text-emerald-600 bg-emerald-500/10 border-emerald-500/20"
                                  >
                                    TLS 1.3
                                  </Badge>
                                )}
                                <Badge variant="outline" className="text-[9px] font-mono text-muted-foreground">
                                  {b.retention_period_days}d Retention
                                </Badge>
                              </div>
                            </div>

                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                              onClick={() =>
                                setUnbindingTarget({
                                  integrationId: integ.id,
                                  datasetId: b.data_set_id,
                                  datasetName: b.dataset_name || "Dataset",
                                  integrationCode: integ.itsm_integration_id,
                                })
                              }
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="lg:col-span-5 space-y-3 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                          <Shield className="w-4 h-4 text-emerald-600" />
                          Transfer Integrity Pattern
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-[11px] gap-1 px-2.5 shadow-2xs"
                          onClick={() => setDeclaringPatternIntegrationId(integ.id)}
                        >
                          {hasPattern ? "Update Pattern" : "Declare Pattern"}
                        </Button>
                      </div>

                      {hasPattern ? (
                        <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 text-xs space-y-1.5">
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span className="font-semibold text-foreground">
                              {integ.integrity_pattern.replace(/_/g, " ")}
                            </span>
                          </div>
                          {integ.integrity_pattern_details && (
                            <p className="text-[11px] text-muted-foreground line-clamp-3 leading-relaxed">
                              {integ.integrity_pattern_details}
                            </p>
                          )}
                        </div>
                      ) : (
                        <div className="p-3 rounded-lg border border-dashed border-amber-500/30 bg-amber-500/5 text-xs text-amber-700 dark:text-amber-400">
                          Pattern Undeclared
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-border flex items-center justify-end gap-2">
                      {canSubmitCertification && (
                        <Button
                          size="sm"
                          onClick={() => handleSubmitCertification(integ)}
                          disabled={submitCertificationMut.isPending}
                          className="h-8 text-xs font-semibold gap-1.5 shadow-xs"
                        >
                          <Send className="w-3.5 h-3.5" />
                          Submit for Certification
                        </Button>
                      )}

                      {isPendingVerification && (
                        <Button
                          size="sm"
                          onClick={() => setVerifyingIntegrationId(integ.id)}
                          className="h-8 text-xs font-semibold gap-1.5 shadow-xs"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Steward Sign-Off
                        </Button>
                      )}

                      {isCompliant && (
                        <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold px-2 py-1 bg-emerald-500/10 rounded-md">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>Certified Compliant</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Pagination & Density Footer */}
      {filteredIntegrations.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-3 border-t border-border text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span>
              Showing <strong>{startIndex + 1}</strong> to{" "}
              <strong>{Math.min(startIndex + integrationPageSize, totalItems)}</strong> of{" "}
              <strong>{totalItems}</strong> integrations
            </span>

            <div className="flex items-center gap-1.5">
              <span>Per page:</span>
              <Select
                value={String(integrationPageSize)}
                onValueChange={(val) => setIntegrationPageSize(Number(val))}
              >
                <SelectTrigger className="h-7 text-xs w-16 bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10" className="text-xs">10</SelectItem>
                  <SelectItem value="25" className="text-xs">25</SelectItem>
                  <SelectItem value="50" className="text-xs">50</SelectItem>
                  <SelectItem value="100" className="text-xs">100</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => setIntegrationPage(currentPage - 1)}
              className="h-7 px-2 text-xs"
            >
              <ChevronLeft className="w-3.5 h-3.5 mr-1" />
              Previous
            </Button>
            <span className="px-2 font-mono text-[11px]">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setIntegrationPage(currentPage + 1)}
              className="h-7 px-2 text-xs"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* shadcn AlertDialog for unbinding a dataset */}
      <AlertDialog
        open={Boolean(unbindingTarget)}
        onOpenChange={(open: boolean) => !open && setUnbindingTarget(null)}
      >
        <AlertDialogContent className="sm:max-w-md">
          <AlertDialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center justify-center text-destructive shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <AlertDialogTitle className="text-base font-bold">
                  Remove Dataset Binding
                </AlertDialogTitle>
                <AlertDialogDescription className="text-xs text-muted-foreground mt-0.5">
                  Unbind dataset from technical data movement scope.
                </AlertDialogDescription>
              </div>
            </div>
          </AlertDialogHeader>

          <div className="py-2 text-xs text-muted-foreground">
            Are you sure you want to remove{" "}
            <strong className="text-foreground">{unbindingTarget?.datasetName}</strong> from
            integration{" "}
            <Badge variant="outline" className="font-mono text-[10px]">
              {unbindingTarget?.integrationCode}
            </Badge>
            ?
            <p className="mt-2 text-[11px] text-amber-600 dark:text-amber-400 bg-amber-500/10 p-2.5 rounded border border-amber-500/20">
              Note: If this leaves the integration with zero bound datasets, the integration will
              immediately transition to <strong>UNGOVERNED</strong> and flag an audit compliance
              warning.
            </p>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => setUnbindingTarget(null)}
              className="h-8 text-xs"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmUnbind}
              disabled={unbindMutation.isPending}
              className="h-8 text-xs bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {unbindMutation.isPending ? "Removing..." : "Remove Binding"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
