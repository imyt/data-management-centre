import React, { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Inbox,
  Clock,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Shield,
  Check,
  X,
  AlertCircle,
  Loader2,
  RefreshCw,
  UserCheck,
} from "lucide-react";
import { usePersona } from "@/context/PersonaContext";
import { api, type StageApprovalTask } from "@/api/client";
import { useInboxUiStore } from "../stores/inbox.store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StewardVerificationQueue } from "./StewardVerificationQueue";
import { verificationApi } from "../api/verificationApi";

export const GovernanceInbox: React.FC = () => {
  const { currentRole } = usePersona();
  const queryClient = useQueryClient();
  const [inboxTab, setInboxTab] = useState<"WORKFLOW" | "VERIFICATIONS">("WORKFLOW");

  // Query Data Steward Verifications for count badge
  const { data: verificationsData } = useQuery({
    queryKey: ["steward-verifications"],
    queryFn: () => verificationApi.listPendingVerifications(),
  });
  const verificationsPendingCount = verificationsData?.summary.total_pending ?? 0;

  // Zustand Store
  const {
    filter,
    setFilter,
    scope,
    setScope,
    activeActionModal,
    openActionModal,
    closeActionModal,
  } = useInboxUiStore();

  const [decisionNotes, setDecisionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  // TanStack Query: Fetch Tasks
  const {
    data: tasks = [],
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["workflow-tasks", filter, scope, currentRole],
    queryFn: () =>
      api.getWorkflowTasks({
        role: scope === "MY_ROLE" ? currentRole : undefined,
        status: filter,
      }),
  });

  // TanStack Mutation: Approve or Reject
  const actionMutation = useMutation({
    mutationFn: ({
      taskId,
      decision,
      notes,
    }: {
      taskId: string;
      decision: "APPROVED" | "REJECTED";
      notes?: string;
    }) =>
      api.actionWorkflowTask(taskId, {
        decision,
        decision_notes: notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      closeActionModal();
      setDecisionNotes("");
      setActionError(null);
    },
    onError: (err: unknown) => {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to execute workflow decision";
      setActionError(errorMsg);
    },
  });

  // Calculate SLA countdown
  const getSlaInfo = (dueAtStr: string) => {
    try {
      const dueTime = new Date(dueAtStr).getTime();
      const diffMs = dueTime - Date.now();
      const hours = Math.round(diffMs / (1000 * 60 * 60));
      return {
        hours,
        isOverdue: hours < 0,
        isUrgent: hours <= 24 && hours >= 0,
        text:
          hours < 0
            ? `${Math.abs(hours)}h overdue`
            : `${hours}h remaining`,
      };
    } catch {
      return { hours: 48, isOverdue: false, isUrgent: false, text: "48h remaining" };
    }
  };

  const handleConfirmAction = () => {
    if (!activeActionModal.taskId || !activeActionModal.decision) return;
    setActionError(null);
    actionMutation.mutate({
      taskId: activeActionModal.taskId,
      decision: activeActionModal.decision,
      notes: decisionNotes.trim() || undefined,
    });
  };

  const pendingCount = tasks.filter((t) => t.decision === "PENDING").length;

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Action Bar */}
      <div className="h-12 border-b border-border bg-card px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
            <Inbox className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-bold text-foreground">Governance Task Inbox</h1>
            <p className="text-[10px] text-muted-foreground">
              Multi-stage approval queues, workflow delegations, and SLA enforcement sweeps.
            </p>
          </div>
        </div>

        {/* Filter Tabs & Scope Selectors */}
        <div className="flex items-center space-x-2">
          {/* Scope Toggle: My Role vs All */}
          <div className="flex items-center space-x-1 bg-muted/40 p-0.5 rounded-md border border-border">
            <button
              onClick={() => setScope("MY_ROLE")}
              className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors cursor-pointer ${
                scope === "MY_ROLE"
                  ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              title={`Filtered to tasks for ${currentRole}`}
            >
              My Role ({currentRole})
            </button>
            <button
              onClick={() => setScope("ALL_ROLES")}
              className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors cursor-pointer ${
                scope === "ALL_ROLES"
                  ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All Queues
            </button>
          </div>

          {/* Status Tabs */}
          <div className="flex items-center space-x-1 bg-muted/50 p-0.5 rounded-md border border-border">
            <button
              onClick={() => setFilter("PENDING")}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                filter === "PENDING"
                  ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Awaiting Action {filter === "PENDING" && !isLoading ? `(${tasks.length})` : ""}
            </button>
            <button
              onClick={() => setFilter("APPROVED")}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                filter === "APPROVED"
                  ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Approved
            </button>
            <button
              onClick={() => setFilter("ALL")}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                filter === "ALL"
                  ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All History
            </button>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh inbox"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Sub-Navigation: Asset Approvals vs Steward Two-Party Verifications */}
      <div className="border-b border-border bg-card/60 px-4 py-2 flex items-center justify-between shrink-0 shadow-2xs">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setInboxTab("WORKFLOW")}
            className={`flex items-center space-x-2 px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              inboxTab === "WORKFLOW"
                ? "bg-primary text-primary-foreground shadow-xs font-bold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-border/60"
            }`}
          >
            <Inbox className="w-3.5 h-3.5" />
            <span>Asset Workflow Approvals</span>
            {pendingCount > 0 && (
              <Badge variant={inboxTab === "WORKFLOW" ? "secondary" : "outline"} className="text-[10px] font-mono px-1 py-0 h-4">
                {pendingCount}
              </Badge>
            )}
          </button>

          <button
            onClick={() => setInboxTab("VERIFICATIONS")}
            className={`flex items-center space-x-2 px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              inboxTab === "VERIFICATIONS"
                ? "bg-primary text-primary-foreground shadow-xs font-bold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-border/60"
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Attestation & Waiver Verification</span>
            {verificationsPendingCount > 0 && (
              <Badge variant="destructive" className="text-[10px] font-mono px-1.5 py-0 h-4 animate-pulse">
                {verificationsPendingCount}
              </Badge>
            )}
          </button>
        </div>

        <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
          <UserCheck className="w-3.5 h-3.5 text-primary" />
          <span>Active Role: <strong className="text-foreground">{currentRole}</strong></span>
        </div>
      </div>

      {inboxTab === "VERIFICATIONS" ? (
        <div className="flex-1 overflow-y-auto p-6 max-w-6xl w-full mx-auto">
          <StewardVerificationQueue />
        </div>
      ) : (
        /* Main Task List */
        <div className="flex-1 overflow-y-auto p-4 max-w-6xl w-full mx-auto space-y-3">
          {/* Info Banner */}
          <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 text-foreground">
            <Shield className="w-4 h-4 text-primary shrink-0" />
            <span>
              Signed in as <strong className="font-semibold">{currentRole}</strong>.
              {scope === "MY_ROLE"
                ? " Showing tasks routed to your role."
                : " Showing tasks across all governance roles."}
            </span>
          </div>
          <div className="flex items-center space-x-3 text-[10px] text-muted-foreground font-mono">
            <span>SLA Sweep: Active (hourly)</span>
            {pendingCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 font-bold">
                {pendingCount} Pending Sign-Off
              </span>
            )}
          </div>
        </div>

        {/* Task Cards / Table */}
        <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
          <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-muted/40 border-b border-border text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            <span className="col-span-4">Governance Target</span>
            <span className="col-span-3">Workflow Stage</span>
            <span className="col-span-2">Proposer</span>
            <span className="col-span-1">SLA Window</span>
            <span className="col-span-2 text-right">Actions</span>
          </div>

          {isLoading ? (
            <div className="py-16 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Loading governance approval queue...</span>
            </div>
          ) : (
            <div className="divide-y divide-border/60">
              {tasks.map((task: StageApprovalTask) => {
                const sla = getSlaInfo(task.due_at);
                const isPending = task.decision === "PENDING";
                const isApproved = task.decision === "APPROVED";

                return (
                  <div
                    key={task.id}
                    className="grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-accent/40 transition-colors text-xs"
                  >
                    {/* Target */}
                    <div className="col-span-4 flex items-center space-x-2">
                      <div
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          isPending
                            ? "bg-amber-500"
                            : isApproved
                            ? "bg-emerald-500"
                            : "bg-rose-500"
                        }`}
                      />
                      <div className="truncate">
                        <Link
                          to="/catalog"
                          search={{
                            assetId: task.asset_head_id || undefined,
                            domainId: task.asset_domain_id || undefined,
                          }}
                          className="font-semibold text-foreground hover:underline cursor-pointer"
                        >
                          {task.asset_name || "Governance Target"}
                        </Link>
                        <span className="ml-1.5 font-mono text-[10px] text-muted-foreground">
                          v{task.asset_version_number || 1}
                        </span>
                      </div>
                    </div>

                    {/* Stage & Role */}
                    <div className="col-span-3 flex flex-col space-y-0.5">
                      <div className="flex items-center space-x-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-foreground border border-border">
                          {task.stage_name || `Stage ${task.stage_order || 1}`}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-medium bg-primary/10 text-primary">
                          {task.assigned_role}
                        </span>
                      </div>
                      {task.decision_notes && (
                        <p className="text-[10px] text-muted-foreground italic truncate">
                          "{task.decision_notes}"
                        </p>
                      )}
                    </div>

                    {/* Proposer */}
                    <div className="col-span-2 text-muted-foreground truncate flex items-center space-x-1">
                      <UserCheck className="w-3 h-3 text-muted-foreground shrink-0" />
                      <span className="truncate">{task.proposer_name || "Initiator"}</span>
                    </div>

                    {/* SLA Window */}
                    <div className="col-span-1 flex items-center space-x-1">
                      <Clock
                        className={`w-3.5 h-3.5 ${
                          sla.isOverdue
                            ? "text-rose-500"
                            : sla.isUrgent
                            ? "text-amber-500 animate-pulse"
                            : "text-muted-foreground"
                        }`}
                      />
                      <span
                        className={`text-[10px] font-mono font-medium ${
                          sla.isOverdue
                            ? "text-rose-600 dark:text-rose-400 font-bold"
                            : sla.isUrgent
                            ? "text-amber-600 dark:text-amber-400 font-bold"
                            : "text-muted-foreground"
                        }`}
                      >
                        {sla.text}
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div className="col-span-2 flex items-center justify-end space-x-1.5">
                      {isPending ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() =>
                              openActionModal(
                                task.id,
                                "APPROVED",
                                task.asset_name || undefined
                              )
                            }
                            className="h-6 text-[11px] px-2 font-medium gap-1 shadow-xs"
                            title="Approve stage sign-off"
                          >
                            <Check className="w-3 h-3" />
                            <span>Approve</span>
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() =>
                              openActionModal(
                                task.id,
                                "REJECTED",
                                task.asset_name || undefined
                              )
                            }
                            className="h-6 text-[11px] px-2 font-medium gap-1"
                            title="Reject draft and return to author"
                          >
                            <X className="w-3 h-3" />
                            <span>Reject</span>
                          </Button>
                        </>
                      ) : isApproved ? (
                        <Badge variant="soft" className="font-mono text-[10px] gap-1">
                          <CheckCircle2 className="w-3 h-3 text-primary" />
                          <span>Approved</span>
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="font-mono text-[10px] gap-1">
                          <XCircle className="w-3 h-3" />
                          <span>Rejected</span>
                        </Badge>
                      )}

                      {/* Review Link */}
                      <Link
                        to="/catalog"
                        search={{
                          assetId: task.asset_head_id || undefined,
                          domainId: task.asset_domain_id || undefined,
                        }}
                        className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                        title="View Asset in Catalog"
                      >
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}

              {tasks.length === 0 && (
                <div className="py-16 text-center text-xs text-muted-foreground space-y-1">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
                  <p className="font-semibold text-foreground">
                    All clear! No tasks awaiting approval.
                  </p>
                  <p className="text-[11px]">
                    Tasks for {currentRole} or within selected filter will appear here.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      )}

      {/* Decision Sign-Off Modal */}
      {activeActionModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-md w-full p-4 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center space-x-2">
                {activeActionModal.decision === "APPROVED" ? (
                  <div className="w-7 h-7 rounded bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                ) : (
                  <div className="w-7 h-7 rounded bg-rose-500/10 text-rose-600 flex items-center justify-center">
                    <AlertCircle className="w-4 h-4" />
                  </div>
                )}
                <div>
                  <h3 className="text-xs font-bold text-foreground">
                    {activeActionModal.decision === "APPROVED"
                      ? "Approve Stage Sign-Off"
                      : "Reject Asset Version"}
                  </h3>
                  <p className="text-[10px] text-muted-foreground">
                    Target:{" "}
                    <strong className="text-foreground">
                      {activeActionModal.assetName || "Selected Asset"}
                    </strong>
                  </p>
                </div>
              </div>
              <button
                onClick={closeActionModal}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-2 bg-destructive/10 border border-destructive/20 text-destructive text-[11px] rounded">
                {actionError}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[11px] font-medium text-foreground">
                Decision Notes & Governance Rationale
              </label>
              <textarea
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                rows={3}
                placeholder={
                  activeActionModal.decision === "APPROVED"
                    ? "Optional notes explaining compliance or sign-off rationale..."
                    : "Please state the reason for rejecting this proposal..."
                }
                className="w-full text-xs p-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={closeActionModal}
                disabled={actionMutation.isPending}
                className="h-7 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant={activeActionModal.decision === "APPROVED" ? "default" : "destructive"}
                onClick={handleConfirmAction}
                disabled={actionMutation.isPending}
                className="h-7 text-xs font-semibold gap-1"
              >
                {actionMutation.isPending ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <span>
                    Confirm{" "}
                    {activeActionModal.decision === "APPROVED"
                      ? "Approval"
                      : "Rejection"}
                  </span>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
