import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, CheckCircle2 } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const RemediatePurgeModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeIssue, remediationModalType, closeRemediationModal } = useWorkbenchUiStore();

  const isOpen = remediationModalType === "PURGE" && activeIssue !== null;
  const storageId = activeIssue?.storage_control?.id || "";

  const [notes, setNotes] = useState<string>(
    "Executed automated partition drop and AWS KMS cryptographic key destruction for expired ledger records."
  );

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.remediatePurge({
        issue_id: activeIssue!.id,
        storage_control_id: storageId,
        attestation_notes: notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      queryClient.invalidateQueries({ queryKey: ["storage-controls"] });
      closeRemediationModal();
    },
  });

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeRemediationModal()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Attest Retention Purge Cycle
              </DialogTitle>
              <DialogDescription className="text-xs">
                Remediate defect <strong className="text-foreground">{activeIssue.rule_code}</strong> for repository{" "}
                <span className="font-mono text-primary font-semibold">
                  {activeIssue.storage_control?.storage_name || "Repository"}
                </span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          <div className="bg-muted/40 p-3 rounded-lg border border-border/60 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Retention Policy Window:</span>
              <span className="font-bold font-mono text-foreground">
                {activeIssue.storage_control?.retention_period_days || 90} Days
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Storage Engine:</span>
              <span className="font-semibold text-foreground">
                {activeIssue.storage_control?.storage_type || "POSTGRESQL"}
              </span>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Purge Attestation / Audit Execution Log</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide execution batch ID, partition drop confirmation, or cryptographic key destruction details..."
              className="text-xs min-h-[90px] bg-background"
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={closeRemediationModal} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending || !notes}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Attesting..." : "Attest Purge & Clear Defect"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
