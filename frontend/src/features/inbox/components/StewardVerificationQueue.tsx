import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  XCircle,
  ArrowRightLeft,
  ShieldAlert,
  Loader2,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  verificationApi,
  type PendingIntegrationItem,
  type PendingWaiverItem,
} from "../api/verificationApi";

export const StewardVerificationQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [filterType, setFilterType] = useState<"ALL" | "INTEGRATIONS" | "WAIVERS">("ALL");

  // Review Dialog State
  const [activeReviewItem, setActiveReviewItem] = useState<{
    type: "INTEGRATION" | "WAIVER";
    integration?: PendingIntegrationItem;
    waiver?: PendingWaiverItem;
    decision: "APPROVE" | "REJECT";
  } | null>(null);

  const [decisionNotes, setDecisionNotes] = useState("");
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Fetch pending verifications
  const { data, isLoading } = useQuery({
    queryKey: ["steward-verifications"],
    queryFn: () => verificationApi.listPendingVerifications(),
  });

  // Review Mutations
  const integrationMutation = useMutation({
    mutationFn: ({ id, approved, notes }: { id: string; approved: boolean; notes: string }) =>
      verificationApi.reviewIntegration(id, approved, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["steward-verifications"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      queryClient.invalidateQueries({ queryKey: ["application-integrations"] });
      setActiveReviewItem(null);
      setDecisionNotes("");
      setReviewError(null);
    },
    onError: (err: unknown) => {
      setReviewError(err instanceof Error ? err.message : "Failed to review integration.");
    },
  });

  const waiverMutation = useMutation({
    mutationFn: ({ id, approved, notes }: { id: string; approved: boolean; notes: string }) =>
      verificationApi.reviewExemption(id, approved, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["steward-verifications"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      setActiveReviewItem(null);
      setDecisionNotes("");
      setReviewError(null);
    },
    onError: (err: unknown) => {
      setReviewError(err instanceof Error ? err.message : "Failed to review waiver.");
    },
  });

  const handleConfirmDecision = () => {
    if (!activeReviewItem) return;
    setReviewError(null);

    const notes = decisionNotes.trim() || (activeReviewItem.decision === "APPROVE" ? "Approved and certified by Data Steward." : "Rejected by Data Steward.");

    if (activeReviewItem.type === "INTEGRATION" && activeReviewItem.integration) {
      integrationMutation.mutate({
        id: activeReviewItem.integration.id,
        approved: activeReviewItem.decision === "APPROVE",
        notes,
      });
    } else if (activeReviewItem.type === "WAIVER" && activeReviewItem.waiver) {
      waiverMutation.mutate({
        id: activeReviewItem.waiver.id,
        approved: activeReviewItem.decision === "APPROVE",
        notes,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-muted-foreground flex items-center justify-center space-x-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading verification queue...</span>
      </div>
    );
  }

  const integrations = data?.integrations || [];
  const waivers = data?.waivers || [];

  const showIntegrations = filterType === "ALL" || filterType === "INTEGRATIONS";
  const showWaivers = filterType === "ALL" || filterType === "WAIVERS";

  const totalPending = (data?.summary.total_pending ?? 0);

  return (
    <div className="space-y-6">
      {/* Top Banner & Summary */}
      <div className="bg-card border border-border p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            <span>Two-Party Governance Verification Queue</span>
            {totalPending > 0 && (
              <Badge variant="destructive" className="text-[10px] font-mono h-4 px-1.5">
                {totalPending} Awaiting Steward Review
              </Badge>
            )}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Four-eyes dual-party review loop. Review application owner transfer pattern attestations and risk exemption waivers.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={filterType === "ALL" ? "default" : "outline"}
            onClick={() => setFilterType("ALL")}
            className="h-7 text-xs font-semibold px-2.5"
          >
            All Pending ({totalPending})
          </Button>
          <Button
            size="sm"
            variant={filterType === "INTEGRATIONS" ? "default" : "outline"}
            onClick={() => setFilterType("INTEGRATIONS")}
            className="h-7 text-xs font-semibold px-2.5 gap-1.5"
          >
            <ArrowRightLeft className="w-3 h-3" />
            <span>Integrations ({integrations.length})</span>
          </Button>
          <Button
            size="sm"
            variant={filterType === "WAIVERS" ? "default" : "outline"}
            onClick={() => setFilterType("WAIVERS")}
            className="h-7 text-xs font-semibold px-2.5 gap-1.5"
          >
            <ShieldAlert className="w-3 h-3" />
            <span>Risk Waivers ({waivers.length})</span>
          </Button>
        </div>
      </div>

      {/* Main Review Items List */}
      <div className="space-y-4">
        {totalPending === 0 && (
          <div className="bg-muted/20 border border-dashed border-border rounded-xl p-12 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <h3 className="text-sm font-bold text-foreground">All Dual-Party Reviews Cleared</h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              There are no transfer pattern attestations or risk waivers awaiting Data Steward review. All application conduits are certified.
            </p>
          </div>
        )}

        {/* 1. Pending Integrations */}
        {showIntegrations &&
          integrations.map((integ) => (
            <Card
              key={integ.id}
              className="border-amber-500/30 bg-card hover:border-amber-500/50 transition-colors shadow-xs"
            >
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono text-[10px] bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30 font-bold">
                        TRANSFER PATTERN REVIEW
                      </Badge>
                      <span className="font-mono text-xs font-bold text-foreground">
                        {integ.itsm_integration_id}
                      </span>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs font-medium text-foreground">
                        {integ.app_name}
                      </span>
                      <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
                        {integ.app_ci}
                      </Badge>
                    </div>

                    <div className="text-xs text-muted-foreground flex items-center gap-2 pt-0.5">
                      <span className="font-semibold text-foreground">Direction:</span>
                      <span className="font-mono">{integ.direction}</span>
                      <span>→</span>
                      <span>Target: <strong className="text-foreground">{integ.partner_app_name}</strong></span>
                      <span>({integ.transfer_type} • {integ.frequency})</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() =>
                        setActiveReviewItem({
                          type: "INTEGRATION",
                          integration: integ,
                          decision: "REJECT",
                        })
                      }
                      className="h-7 text-xs px-2.5 font-semibold gap-1"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </Button>
                    <Button
                      size="sm"
                      onClick={() =>
                        setActiveReviewItem({
                          type: "INTEGRATION",
                          integration: integ,
                          decision: "APPROVE",
                        })
                      }
                      className="h-7 text-xs px-2.5 font-bold gap-1 shadow-xs"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Certify & Sign-Off</span>
                    </Button>
                  </div>
                </div>

                {/* Evidence & Technical Details Block */}
                <div className="bg-muted/40 p-3 rounded-lg border border-border/60 text-xs space-y-2">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <div className="text-muted-foreground font-medium text-[11px]">
                        Declared Transfer Pattern:
                      </div>
                      <div className="font-mono font-bold text-foreground mt-0.5">
                        {integ.integrity_pattern}
                      </div>
                      <div className="text-muted-foreground text-[11px] mt-1 font-sans">
                        Implementation Notes: {integ.integrity_pattern_details || "No technical notes provided"}
                      </div>
                    </div>

                    <div>
                      <div className="text-muted-foreground font-medium text-[11px]">
                        Bound Datasets ({integ.bound_datasets_count}):
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {integ.bound_datasets.map((ds) => (
                          <Badge key={ds.id} variant="secondary" className="text-[10px] font-mono">
                            {ds.name} ({ds.isr_classification})
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

        {/* 2. Pending Risk Waivers */}
        {showWaivers &&
          waivers.map((waiver) => (
            <Card
              key={waiver.id}
              className="border-primary/30 bg-card hover:border-primary/50 transition-colors shadow-xs"
            >
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="soft" className="font-mono text-[10px] font-bold">
                        COMPLIANCE RISK WAIVER
                      </Badge>
                      <span className="font-mono text-xs font-bold text-foreground">
                        {waiver.rule_code}
                      </span>
                      <Badge variant="destructive" className="text-[10px] font-mono">
                        {waiver.severity}
                      </Badge>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs font-medium text-foreground">
                        {waiver.app_name}
                      </span>
                      <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
                        {waiver.app_ci}
                      </Badge>
                    </div>

                    <div className="text-xs font-semibold text-foreground">
                      {waiver.issue_title}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() =>
                        setActiveReviewItem({
                          type: "WAIVER",
                          waiver: waiver,
                          decision: "REJECT",
                        })
                      }
                      className="h-7 text-xs px-2.5 font-semibold gap-1"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject Waiver</span>
                    </Button>
                    <Button
                      size="sm"
                      onClick={() =>
                        setActiveReviewItem({
                          type: "WAIVER",
                          waiver: waiver,
                          decision: "APPROVE",
                        })
                      }
                      className="h-7 text-xs px-2.5 font-bold gap-1 shadow-xs"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve Waiver</span>
                    </Button>
                  </div>
                </div>

                {/* Justification & Compensating Controls */}
                <div className="bg-muted/40 p-3 rounded-lg border border-border/60 text-xs space-y-2">
                  <div>
                    <div className="text-muted-foreground font-medium text-[11px]">
                      Architectural Justification:
                    </div>
                    <p className="text-foreground mt-0.5">{waiver.justification}</p>
                  </div>

                  <div className="border-t border-border/40 pt-2">
                    <div className="text-muted-foreground font-medium text-[11px] flex items-center gap-1.5">
                      <AlertTriangle className="w-3 h-3 text-amber-500" />
                      <span>Compensating Security Controls:</span>
                    </div>
                    <p className="text-foreground font-mono text-[11px] mt-0.5 bg-background p-2 rounded border border-border">
                      {waiver.compensating_controls}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                    <span>Requested by: <strong className="text-foreground">{waiver.requested_by_name}</strong></span>
                    <span>Expires: <strong className="font-mono text-foreground">{new Date(waiver.expires_at).toLocaleDateString()}</strong></span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
      </div>

      {/* Review Confirmation Dialog */}
      {activeReviewItem && (
        <Dialog open={!!activeReviewItem} onOpenChange={() => setActiveReviewItem(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                {activeReviewItem.decision === "APPROVE" ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    <span>Confirm Data Steward Sign-Off</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-destructive" />
                    <span>Reject & Re-Open Compliance Defect</span>
                  </>
                )}
              </DialogTitle>
              <DialogDescription className="text-xs">
                {activeReviewItem.decision === "APPROVE"
                  ? "Grant formal steward certification. This transitions the technical asset to COMPLIANT and mints an immutable audit event."
                  : "Reject the application owner's submission. The defect will re-open in their Workbench with SLA countdown active."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {reviewError && (
                <div className="p-2.5 rounded-lg bg-destructive/15 border border-destructive/30 text-destructive text-xs font-medium">
                  {reviewError}
                </div>
              )}

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  Data Steward Review Notes & Audit Rationale
                </Label>
                <Textarea
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  placeholder={
                    activeReviewItem.decision === "APPROVE"
                      ? "Record verified cryptographic hash implementation, architecture review notes, or compensating control sign-off..."
                      : "Explain why this submission does not satisfy policy requirements and what the Application Owner must fix..."
                  }
                  className="text-xs min-h-[90px]"
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveReviewItem(null)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant={activeReviewItem.decision === "APPROVE" ? "default" : "destructive"}
                onClick={handleConfirmDecision}
                disabled={integrationMutation.isPending || waiverMutation.isPending}
                className="text-xs font-bold"
              >
                {integrationMutation.isPending || waiverMutation.isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    <span>Recording Decision...</span>
                  </>
                ) : activeReviewItem.decision === "APPROVE" ? (
                  "Confirm & Certify Asset"
                ) : (
                  "Reject & Return Defect"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
