import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, ShieldCheck, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { verifyCertificationMutation } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

export const StewardVerificationModal: React.FC = () => {
  const { verifyingIntegrationId, setVerifyingIntegrationId } = useDataMovementUiStore();
  const queryClient = useQueryClient();

  const [decision, setDecision] = React.useState<"APPROVED" | "REJECTED">("APPROVED");
  const [stewardName, setStewardName] = React.useState<string>("Sarah Jenkins (Lead Steward)");
  const [notes, setNotes] = React.useState<string>("");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const verifyMutation = useMutation({
    ...verifyCertificationMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setVerifyingIntegrationId(null);
      setNotes("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to submit verification.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyingIntegrationId) return;

    if (decision === "REJECTED" && (!notes.trim() || notes.trim().length < 5)) {
      setErrorMessage("Please specify rejection reason and corrective instructions for App Owner.");
      return;
    }

    verifyMutation.mutate({
      path: { integration_id: verifyingIntegrationId },
      body: {
        approved: decision === "APPROVED",
        decision_notes: notes.trim()
          ? `${stewardName}: ${notes.trim()}`
          : `${stewardName}: Verified and certified compliant.`,
      },
    });
  };

  const handleClose = () => {
    setVerifyingIntegrationId(null);
    setNotes("");
    setErrorMessage(null);
  };

  return (
    <Dialog open={Boolean(verifyingIntegrationId)} onOpenChange={(open: boolean) => !open && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Steward Verification Sign-Off</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Review declared transfer patterns and bound dataset sensitivities to grant compliance certification.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {errorMessage && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-xs text-destructive flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="text-xs font-semibold">Verification Decision *</Label>
            <RadioGroup
              value={decision}
              onValueChange={(val: string) => setDecision(val as "APPROVED" | "REJECTED")}
              className="grid grid-cols-2 gap-3"
            >
              <Label
                htmlFor="opt-approve"
                className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all ${
                  decision === "APPROVED"
                    ? "border-primary bg-primary/10 text-primary font-medium"
                    : "border-border hover:bg-muted/40"
                }`}
              >
                <RadioGroupItem value="APPROVED" id="opt-approve" />
                <CheckCircle2 className="w-4 h-4 text-primary" />
                <span className="text-xs font-semibold">Approve & Certify</span>
              </Label>

              <Label
                htmlFor="opt-reject"
                className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all ${
                  decision === "REJECTED"
                    ? "border-destructive bg-destructive/10 text-destructive font-medium"
                    : "border-border hover:bg-muted/40"
                }`}
              >
                <RadioGroupItem value="REJECTED" id="opt-reject" />
                <XCircle className="w-4 h-4 text-destructive" />
                <span className="text-xs font-semibold">Reject & Remediate</span>
              </Label>
            </RadioGroup>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="steward-name" className="text-xs font-semibold">
              Steward Reviewer Name
            </Label>
            <Input
              id="steward-name"
              type="text"
              value={stewardName}
              onChange={(e) => setStewardName(e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="decision-notes" className="text-xs font-semibold">
              {decision === "REJECTED" ? "Rejection Reason & Required Remediation *" : "Verification Notes (Optional)"}
            </Label>
            <Textarea
              id="decision-notes"
              placeholder={
                decision === "REJECTED"
                  ? "Specify why the integrity pattern or transport encryption is insufficient..."
                  : "Additional compliance audit comments or certification remarks..."
              }
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="text-xs resize-none"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" size="sm" onClick={handleClose} className="h-8 text-xs">
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={verifyMutation.isPending}
              variant={decision === "APPROVED" ? "default" : "destructive"}
              className="h-8 text-xs font-semibold shadow-xs"
            >
              {verifyMutation.isPending
                ? "Submitting..."
                : decision === "APPROVED"
                ? "Grant Compliance Sign-Off"
                : "Reject & Flag for Remediation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
