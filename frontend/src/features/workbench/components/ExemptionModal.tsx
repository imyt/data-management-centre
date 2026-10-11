import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, CheckCircle2 } from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const ExemptionModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeIssue, remediationModalType, closeRemediationModal } = useWorkbenchUiStore();

  const isOpen = remediationModalType === "EXEMPTION" && activeIssue !== null;

  const [justification, setJustification] = useState<string>(
    "Legacy batch pipeline architecture cannot support real-time cryptographic hashing until scheduled Q3 containerization sprint."
  );
  const [controls, setControls] = useState<string>(
    "Compensating control: Daily row-count reconciliation and secondary perimeter VPN IP whitelisting enforced."
  );
  const [durationDays, setDurationDays] = useState<number>(30);

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.requestExemption({
        issue_id: activeIssue!.id,
        justification,
        compensating_controls: controls,
        duration_days: durationDays,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
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
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Request Compliance Exemption Waiver
              </DialogTitle>
              <DialogDescription className="text-xs">
                Submit formal risk waiver for <strong className="text-foreground">{activeIssue.rule_code}</strong>. Suspends SLA countdown pending audit review.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Business Justification & Architectural Constraint</Label>
            <Textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Explain why immediate remediation is impossible (e.g. legacy mainframe dependency)..."
              className="text-xs min-h-[70px] bg-background"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Compensating Security Controls</Label>
            <Textarea
              value={controls}
              onChange={(e) => setControls(e.target.value)}
              placeholder="Detail alternative compensating security controls deployed to mitigate the risk..."
              className="text-xs min-h-[70px] bg-background"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Requested Waiver Duration</Label>
            <Select
              value={durationDays.toString()}
              onValueChange={(val) => setDurationDays(parseInt(val, 10))}
            >
              <SelectTrigger className="h-8 text-xs bg-background">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30" className="text-xs">30 Days (Temporary Sprint Delay)</SelectItem>
                <SelectItem value="60" className="text-xs">60 Days (Quarterly Release Window)</SelectItem>
                <SelectItem value="90" className="text-xs">90 Days (Multi-Team Refactoring)</SelectItem>
                <SelectItem value="180" className="text-xs">180 Days (Major System Migration)</SelectItem>
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
            disabled={mutation.isPending || !justification || !controls}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Submitting..." : "Submit Waiver & Pause SLA"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
