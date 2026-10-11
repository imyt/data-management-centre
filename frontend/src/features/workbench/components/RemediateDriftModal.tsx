import React, { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, CheckCircle2 } from "lucide-react";
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
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const RemediateDriftModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeIssue, remediationModalType, closeRemediationModal, selectedAppHeadId } = useWorkbenchUiStore();

  const isOpen = remediationModalType === "DRIFT" && activeIssue !== null;

  const { data: columns = [] } = useQuery({
    queryKey: ["physical-columns", selectedAppHeadId, "drift"],
    queryFn: () => workbenchApi.listColumns(selectedAppHeadId!, { drift_status: "ADDED_UNCLASSIFIED" }),
    enabled: !!selectedAppHeadId && isOpen,
  });

  const [formState, setFormState] = useState<
    Record<
      string,
      {
        is_pii: boolean;
        masking_strategy: string;
        isr_classification: string;
        business_term_name: string;
      }
    >
  >({});

  useEffect(() => {
    if (columns.length > 0) {
      const initial: Record<string, any> = {};
      columns.forEach((c) => {
        initial[c.id] = {
          is_pii: c.is_pii,
          masking_strategy: c.is_pii ? "PARTIAL_MASK" : "NONE",
          isr_classification: c.isr_classification || "INTERNAL",
          business_term_name: c.business_term_name || "",
        };
      });
      setFormState(initial);
    }
  }, [columns]);

  const mutation = useMutation({
    mutationFn: () => {
      const classifications = columns.map((c) => ({
        column_id: c.id,
        is_pii: formState[c.id]?.is_pii ?? c.is_pii,
        masking_strategy: formState[c.id]?.masking_strategy ?? c.masking_strategy,
        isr_classification: formState[c.id]?.isr_classification ?? c.isr_classification,
        business_term_name: formState[c.id]?.business_term_name || undefined,
      }));
      return workbenchApi.remediateDrift({
        issue_id: activeIssue!.id,
        classifications,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      queryClient.invalidateQueries({ queryKey: ["physical-columns"] });
      queryClient.invalidateQueries({ queryKey: ["physical-tables"] });
      closeRemediationModal();
    },
  });

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeRemediationModal()}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">
                Review & Classify Schema Drift
              </DialogTitle>
              <DialogDescription className="text-xs">
                {columns.length} newly harvested physical database fields detected. Assign PII flags, masking algorithms, and risk tiers to sync the baseline.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-3 py-2 pr-1 text-xs">
          {columns.map((col) => {
            const current = formState[col.id] || {
              is_pii: false,
              masking_strategy: "NONE",
              isr_classification: "INTERNAL",
              business_term_name: "",
            };

            return (
              <div
                key={col.id}
                className="p-3.5 rounded-lg border border-border/80 bg-muted/30 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-muted-foreground">{col.table_name}.</span>
                    <strong className="font-mono text-foreground font-bold">{col.column_name}</strong>
                    <Badge variant="outline" className="font-mono text-[10px] bg-background">
                      {col.data_type}
                    </Badge>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono text-amber-600 bg-amber-500/10 border-amber-500/30">
                    ADDED_UNCLASSIFIED
                  </Badge>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center">
                  {/* PII Toggle */}
                  <div className="flex items-center justify-between p-2 rounded-md bg-background border border-border">
                    <Label className="text-[11px] font-semibold cursor-pointer">PII Sensitive</Label>
                    <Switch
                      checked={current.is_pii}
                      onCheckedChange={(checked) =>
                        setFormState((prev) => ({
                          ...prev,
                          [col.id]: {
                            ...prev[col.id],
                            is_pii: checked,
                            masking_strategy: checked ? "PARTIAL_MASK" : "NONE",
                          },
                        }))
                      }
                    />
                  </div>

                  {/* Masking Strategy */}
                  <div>
                    <Label className="text-[11px] font-semibold text-muted-foreground block mb-1">Masking Policy</Label>
                    <Select
                      value={current.masking_strategy}
                      onValueChange={(val) =>
                        setFormState((prev) => ({
                          ...prev,
                          [col.id]: { ...prev[col.id], masking_strategy: val },
                        }))
                      }
                    >
                      <SelectTrigger className="h-7 text-xs bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="NONE" className="text-xs">NONE</SelectItem>
                        <SelectItem value="PARTIAL_MASK" className="text-xs">PARTIAL_MASK</SelectItem>
                        <SelectItem value="HASH_SHA256" className="text-xs">HASH_SHA256</SelectItem>
                        <SelectItem value="TOKENIZE" className="text-xs">TOKENIZE</SelectItem>
                        <SelectItem value="FULL_REDACTION" className="text-xs">FULL_REDACTION</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* ISR Tier */}
                  <div>
                    <Label className="text-[11px] font-semibold text-muted-foreground block mb-1">Security Tier</Label>
                    <Select
                      value={current.isr_classification}
                      onValueChange={(val) =>
                        setFormState((prev) => ({
                          ...prev,
                          [col.id]: { ...prev[col.id], isr_classification: val },
                        }))
                      }
                    >
                      <SelectTrigger className="h-7 text-xs bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="INTERNAL" className="text-xs">INTERNAL</SelectItem>
                        <SelectItem value="RESTRICTED" className="text-xs">RESTRICTED</SelectItem>
                        <SelectItem value="HIGHLY_RESTRICTED" className="text-xs font-bold text-red-600">HIGHLY_RESTRICTED</SelectItem>
                        <SelectItem value="PUBLIC" className="text-xs">PUBLIC</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-border">
          <Button variant="outline" size="sm" onClick={closeRemediationModal} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending || columns.length === 0}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Syncing..." : "Approve Classifications & Sync Baseline"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
