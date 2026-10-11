import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { setIntegrityPatternMutation } from "@/api/client";
import type { IntegrityPatternEnum } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

const PATTERN_OPTIONS: { value: IntegrityPatternEnum; label: string; desc: string }[] = [
  {
    value: "CHECKSUM_HASH_VERIFICATION",
    label: "Checksum Hash Verification (SHA-256 / MD5)",
    desc: "End-to-end cryptographic digest comparison ensuring payload bits are unchanged across boundaries.",
  },
  {
    value: "IDEMPOTENT_DEDUPLICATION",
    label: "Idempotent Deduplication (Natural Key / Bloom Filter)",
    desc: "Exactly-once semantic guarantee filtering out duplicate event deliveries across messaging buses.",
  },
  {
    value: "ROW_COUNT_RECONCILIATION",
    label: "Row Count Reconciliation (Source vs Target)",
    desc: "Automated batch reconciliation checking extract counts match ingested counts.",
  },
  {
    value: "CDC_WATERMARK_AUDIT",
    label: "CDC Watermark & LSN Alignment",
    desc: "Change-data-capture commit log sequence synchronization without transactional data loss.",
  },
  {
    value: "TRANSACTIONAL_TWO_PHASE_COMMIT",
    label: "Transactional Two-Phase Commit (2PC / XA)",
    desc: "Atomic distributed transaction coordinator ensuring all-or-nothing ledger consistency.",
  },
  {
    value: "CONTROL_RECORD_TRAILER",
    label: "Control Record & Trailer Hash Verification",
    desc: "Batch header/trailer control records with file record counts and financial balance hash sums.",
  },
  {
    value: "NONE_UNENFORCED",
    label: "None (Unenforced - Non-Compliant)",
    desc: "No integrity verification mechanism active. Flagged for immediate audit remediation.",
  },
];

export const DeclareIntegrityPatternModal: React.FC = () => {
  const { declaringPatternIntegrationId, setDeclaringPatternIntegrationId } =
    useDataMovementUiStore();
  const queryClient = useQueryClient();

  const [pattern, setPattern] = React.useState<IntegrityPatternEnum>(
    "CHECKSUM_HASH_VERIFICATION"
  );
  const [patternDetails, setPatternDetails] = React.useState<string>("");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const patternMutation = useMutation({
    ...setIntegrityPatternMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setDeclaringPatternIntegrationId(null);
      setPatternDetails("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to declare integrity pattern.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!declaringPatternIntegrationId) return;

    if (!patternDetails.trim() || patternDetails.trim().length < 10) {
      setErrorMessage("Technical implementation details must be at least 10 characters.");
      return;
    }

    patternMutation.mutate({
      path: { integration_id: declaringPatternIntegrationId },
      body: {
        integrity_pattern: pattern,
        integrity_pattern_details: patternDetails.trim(),
      },
    });
  };

  const handleClose = () => {
    setDeclaringPatternIntegrationId(null);
    setPatternDetails("");
    setErrorMessage(null);
  };

  const selectedPatternMeta = PATTERN_OPTIONS.find((p) => p.value === pattern);

  return (
    <Dialog
      open={Boolean(declaringPatternIntegrationId)}
      onOpenChange={(open: boolean) => !open && handleClose()}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Declare Transfer Integrity Pattern
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Certify the technical mechanism used to prevent data loss, corruption, or duplication.
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
          <div className="space-y-1.5">
            <Label htmlFor="pattern-select" className="text-xs font-semibold">
              Integrity Assurance Pattern *
            </Label>
            <Select
              value={pattern}
              onValueChange={(val) => setPattern(val as IntegrityPatternEnum)}
            >
              <SelectTrigger id="pattern-select" className="text-xs h-9">
                <SelectValue placeholder="Select certified pattern..." />
              </SelectTrigger>
              <SelectContent>
                {PATTERN_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="text-xs">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedPatternMeta && (
              <p className="text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded border border-border mt-1 leading-relaxed">
                {selectedPatternMeta.desc}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="pattern-details" className="text-xs font-semibold">
              Technical Implementation Details *
            </Label>
            <Textarea
              id="pattern-details"
              placeholder="e.g., SHA-256 digest computed at source Kafka producer and verified by consumer prior to database commit..."
              value={patternDetails}
              onChange={(e) => setPatternDetails(e.target.value)}
              rows={3}
              className="text-xs resize-none"
            />
            <p className="text-[11px] text-muted-foreground">
              Provide verifiable technical specifics (algorithm, tooling, reconciliation job schedule).
            </p>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleClose}
              className="h-8 text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={patternMutation.isPending}
              className="h-8 text-xs font-semibold shadow-xs"
            >
              {patternMutation.isPending ? "Declaring..." : "Declare & Certify Pattern"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
