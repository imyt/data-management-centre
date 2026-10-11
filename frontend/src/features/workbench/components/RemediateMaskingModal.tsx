import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { EyeOff, CheckCircle2 } from "lucide-react";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const RemediateMaskingModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeIssue, remediationModalType, closeRemediationModal } = useWorkbenchUiStore();

  const isOpen = remediationModalType === "MASKING" && activeIssue !== null;
  const columnId = activeIssue?.physical_column?.id || "";

  const [strategy, setStrategy] = useState<string>("PARTIAL_MASK");

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.remediateMasking({
        issue_id: activeIssue!.id,
        column_id: columnId,
        masking_strategy: strategy,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      queryClient.invalidateQueries({ queryKey: ["physical-columns"] });
      closeRemediationModal();
    },
  });

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeRemediationModal()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <EyeOff className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Configure Column Privacy Masking
              </DialogTitle>
              <DialogDescription className="text-xs">
                Remediate defect <strong className="text-foreground">{activeIssue.rule_code}</strong> for column{" "}
                <span className="font-mono text-primary font-semibold">
                  {activeIssue.physical_column?.column_name || "Field"}
                </span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          <Label className="text-xs font-semibold">Select Dynamic Masking Algorithm</Label>
          <RadioGroup
            value={strategy}
            onValueChange={setStrategy}
            className="space-y-2"
          >
            {[
              {
                id: "PARTIAL_MASK",
                name: "Partial Masking (Last 4 Digits)",
                desc: "Retains suffix for reconciliation while masking prefix (e.g. ***-**-8921)",
              },
              {
                id: "HASH_SHA256",
                name: "Cryptographic SHA-256 Digest",
                desc: "One-way salt hash preserving joins without exposing plaintext",
              },
              {
                id: "TOKENIZE",
                name: "Format-Preserving Tokenization",
                desc: "Replaces sensitive value with high-entropy surrogate vault token",
              },
              {
                id: "FULL_REDACTION",
                name: "Full Redaction",
                desc: "Completely replaces string with constant asterisks (***)",
              },
            ].map((s) => (
              <div
                key={s.id}
                onClick={() => setStrategy(s.id)}
                className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                  strategy === s.id
                    ? "border-primary bg-primary/5 text-foreground"
                    : "border-border hover:bg-muted/40 text-muted-foreground"
                }`}
              >
                <RadioGroupItem value={s.id} id={s.id} className="mt-0.5" />
                <div>
                  <label htmlFor={s.id} className="font-bold text-xs cursor-pointer block text-foreground">
                    {s.name}
                  </label>
                  <span className="text-[11px] leading-snug block mt-0.5 text-muted-foreground">
                    {s.desc}
                  </span>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={closeRemediationModal} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Applying..." : "Enforce Masking & Clear Defect"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
