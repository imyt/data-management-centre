import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, CheckCircle2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { listApplicationDatasetsOptions } from "@/api/client";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const RemediateIntegrityModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeIssue, remediationModalType, closeRemediationModal, selectedAppHeadId } = useWorkbenchUiStore();

  const isOpen = remediationModalType === "INTEGRITY" && activeIssue !== null;
  const integrationId = activeIssue?.integration?.id || "";

  const [pattern, setPattern] = useState<string>("CHECKSUM_HASH_VERIFICATION");
  const [details, setDetails] = useState<string>("SHA-256 digest calculated at source conduit and attested at consumer boundary.");
  const [datasetId, setDatasetId] = useState<string>("");

  const { data: datasets = [] } = useQuery({
    ...listApplicationDatasetsOptions({
      path: { app_head_id: selectedAppHeadId || "" },
    }),
    enabled: !!selectedAppHeadId && isOpen,
  });

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.remediateIntegrity({
        issue_id: activeIssue!.id,
        integration_id: integrationId,
        pattern,
        pattern_details: details,
        dataset_id: datasetId || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      queryClient.invalidateQueries({ queryKey: ["application-integrations"] });
      closeRemediationModal();
    },
  });

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeRemediationModal()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Certify Transfer Integrity Contract
              </DialogTitle>
              <DialogDescription className="text-xs">
                Remediate defect <strong className="text-foreground">{activeIssue.rule_code}</strong> for integration{" "}
                <span className="font-mono text-primary font-semibold">
                  {activeIssue.integration?.itsm_integration_id || "INT"}
                </span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          {/* Pattern Selection */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold">Select Certified Transfer Integrity Pattern</Label>
            <RadioGroup
              value={pattern}
              onValueChange={setPattern}
              className="grid grid-cols-1 sm:grid-cols-2 gap-2"
            >
              {[
                {
                  id: "CHECKSUM_HASH_VERIFICATION",
                  name: "Checksum Hash Verification",
                  desc: "Cryptographic SHA-256 digest validation at arrival",
                },
                {
                  id: "IDEMPOTENT_DEDUPLICATION",
                  name: "Idempotent Deduplication",
                  desc: "Unique message UUIDs with deduplication buffer",
                },
                {
                  id: "ROW_COUNT_RECONCILIATION",
                  name: "Row-Count Reconciliation",
                  desc: "Batch ledger record count reconciliation verification",
                },
                {
                  id: "CDC_WATERMARK_AUDIT",
                  name: "CDC Watermark Audit",
                  desc: "Log sequence number (LSN) stream audit attestation",
                },
              ].map((p) => (
                <div
                  key={p.id}
                  onClick={() => setPattern(p.id)}
                  className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    pattern === p.id
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border hover:bg-muted/40 text-muted-foreground"
                  }`}
                >
                  <RadioGroupItem value={p.id} id={p.id} className="mt-0.5" />
                  <div>
                    <label htmlFor={p.id} className="font-bold text-xs cursor-pointer block text-foreground">
                      {p.name}
                    </label>
                    <span className="text-[11px] leading-snug block mt-0.5 text-muted-foreground">
                      {p.desc}
                    </span>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Technical Details Input */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Implementation Specification / Digest Header</Label>
            <Input
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              placeholder="e.g. SHA-256 checksum digest enforced via Kafka consumer interceptor."
              className="h-8 text-xs bg-background"
            />
          </div>

          {/* Dataset Binding */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Bind Governed Dataset Scope</Label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger className="h-8 text-xs bg-background">
                <SelectValue placeholder="Select governed dataset to bind..." />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id} className="text-xs">
                    <span className="font-medium">{ds.name}</span>{" "}
                    <span className="text-[10px] font-mono text-muted-foreground">
                      ({ds.isr_classification})
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={closeRemediationModal} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending || !details}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Certifying..." : "Certify Pattern & Resolve Defect"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
