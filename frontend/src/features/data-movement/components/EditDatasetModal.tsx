import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Edit2, AlertTriangle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { getDatasetOptions, updateDatasetMutation } from "@/api/client";
import type { IsrClassificationEnum } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

const COMMON_CATEGORIES = [
  "CUSTOMER_PII",
  "FINANCIAL",
  "SETTLEMENT",
  "BRANCH_OPERATIONS",
  "AUDIT",
  "COMPLIANCE",
  "TRANSACTION",
  "CREDIT_RISK",
  "EMPLOYEE_PII",
  "INTERNAL_METRICS",
];

export const EditDatasetModal: React.FC = () => {
  const { editingDatasetId, setEditingDatasetId, selectedAppHeadId } = useDataMovementUiStore();
  const queryClient = useQueryClient();

  const { data: dataset } = useQuery({
    ...getDatasetOptions({
      path: {
        app_head_id: selectedAppHeadId || "",
        dataset_id: editingDatasetId || "",
      },
    }),
    enabled: Boolean(selectedAppHeadId && editingDatasetId),
  });

  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [businessContext, setBusinessContext] = React.useState("");
  const [isrClassification, setIsrClassification] = React.useState<IsrClassificationEnum>("INTERNAL");
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>([]);
  const [customTagInput, setCustomTagInput] = React.useState("");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (dataset) {
      setName(dataset.name);
      setDescription(dataset.description || "");
      setBusinessContext(dataset.business_context);
      setIsrClassification(dataset.isr_classification || "INTERNAL");
      setSelectedCategories(dataset.data_categories || []);
      setErrorMessage(null);
    }
  }, [dataset]);

  const updateMutation = useMutation({
    ...updateDatasetMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setEditingDatasetId(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to update dataset.");
    },
  });

  const isEscalation = React.useMemo(() => {
    if (!dataset) return false;
    const oldIsr = dataset.isr_classification;
    const isrEscalated =
      (oldIsr === "PUBLIC" || oldIsr === "INTERNAL") &&
      (isrClassification === "RESTRICTED" || isrClassification === "HIGHLY_RESTRICTED");
    const piiAdded =
      !(dataset.data_categories || []).includes("CUSTOMER_PII") &&
      selectedCategories.includes("CUSTOMER_PII");
    return isrEscalated || piiAdded;
  }, [dataset, isrClassification, selectedCategories]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppHeadId || !editingDatasetId) return;

    updateMutation.mutate({
      path: {
        app_head_id: selectedAppHeadId,
        dataset_id: editingDatasetId,
      },
      body: {
        name: name.trim(),
        description: description.trim() || undefined,
        business_context: businessContext.trim(),
        isr_classification: isrClassification,
        data_categories: selectedCategories,
      },
    });
  };

  const toggleCategory = (cat: string) => {
    if (selectedCategories.includes(cat)) {
      setSelectedCategories(selectedCategories.filter((c) => c !== cat));
    } else {
      setSelectedCategories([...selectedCategories, cat]);
    }
  };

  const addCustomTag = () => {
    const tag = customTagInput.trim().toUpperCase();
    if (tag && !selectedCategories.includes(tag)) {
      setSelectedCategories([...selectedCategories, tag]);
      setCustomTagInput("");
    }
  };

  return (
    <Dialog open={Boolean(editingDatasetId)} onOpenChange={(open) => { if (!open) setEditingDatasetId(null); }}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center">
              <Edit2 className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Edit Governed Dataset</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Update classification, domain categories, and operational purpose.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {isEscalation && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-md flex items-start gap-2.5 text-xs text-amber-700 dark:text-amber-400">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" />
            <div>
              <strong className="font-semibold block">Sensitivity Escalation Guardrail Active</strong>
              <p className="text-[11px] mt-0.5 leading-relaxed">
                Escalating ISR level or adding CUSTOMER_PII triggers an automated impact audit across all {dataset?.usage_count || 0} bound integrations. Integrations lacking certified integrity patterns or encryption will be flagged as IN_REMEDIATION.
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {errorMessage && (
            <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-md">
              {errorMessage}
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Dataset Name <span className="text-rose-500">*</span>
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-9 text-xs"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Business Context & Purpose <span className="text-rose-500">*</span>
            </label>
            <Textarea
              value={businessContext}
              onChange={(e) => setBusinessContext(e.target.value)}
              className="text-xs min-h-[75px]"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              ISR Classification Tier <span className="text-rose-500">*</span>
            </label>
            <Select
              value={isrClassification}
              onValueChange={(val) => setIsrClassification(val as IsrClassificationEnum)}
            >
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Select classification tier" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PUBLIC" className="text-xs">
                  PUBLIC - Freely shareable without harm
                </SelectItem>
                <SelectItem value="INTERNAL" className="text-xs">
                  INTERNAL - Company confidential, normal operational protection
                </SelectItem>
                <SelectItem value="RESTRICTED" className="text-xs">
                  RESTRICTED - Confidential business data or sensitive customer info
                </SelectItem>
                <SelectItem value="HIGHLY_RESTRICTED" className="text-xs">
                  HIGHLY RESTRICTED - Strict regulatory liability (PCI, Core Banking PII)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">
              Data Domain Categories
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {COMMON_CATEGORIES.map((cat) => {
                const selected = selectedCategories.includes(cat);
                return (
                  <Badge
                    key={cat}
                    variant={selected ? "default" : "outline"}
                    className={`cursor-pointer text-[10px] font-mono select-none transition-colors ${
                      selected ? "bg-primary text-primary-foreground" : "hover:bg-muted text-muted-foreground"
                    }`}
                    onClick={() => toggleCategory(cat)}
                  >
                    {cat}
                  </Badge>
                );
              })}
            </div>

            <div className="flex gap-2">
              <Input
                placeholder="Add custom domain tag..."
                value={customTagInput}
                onChange={(e) => setCustomTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustomTag(); } }}
                className="h-8 text-xs flex-1"
              />
              <Button type="button" variant="outline" size="sm" onClick={addCustomTag} className="h-8 text-xs">
                Add Tag
              </Button>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Technical Documentation / Schema Notes
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="text-xs min-h-[60px]"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setEditingDatasetId(null)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending}
              className="text-xs font-semibold"
            >
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
