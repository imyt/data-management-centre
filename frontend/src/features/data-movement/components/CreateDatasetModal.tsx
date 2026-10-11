import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { createDatasetMutation } from "@/api/client";
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

export const CreateDatasetModal: React.FC = () => {
  const { isCreateDatasetOpen, setCreateDatasetOpen, selectedAppHeadId } = useDataMovementUiStore();
  const queryClient = useQueryClient();

  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [businessContext, setBusinessContext] = React.useState("");
  const [isrClassification, setIsrClassification] = React.useState<IsrClassificationEnum>("INTERNAL");
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>([]);
  const [customTagInput, setCustomTagInput] = React.useState("");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const resetForm = () => {
    setName("");
    setDescription("");
    setBusinessContext("");
    setIsrClassification("INTERNAL");
    setSelectedCategories([]);
    setCustomTagInput("");
    setErrorMessage(null);
  };

  const createMutation = useMutation({
    ...createDatasetMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setCreateDatasetOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to create dataset.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppHeadId) return;

    if (!name.trim()) {
      setErrorMessage("Dataset Name is required.");
      return;
    }
    if (businessContext.trim().length < 10) {
      setErrorMessage("Business Context must be at least 10 characters explaining intended purpose.");
      return;
    }

    createMutation.mutate({
      path: { app_head_id: selectedAppHeadId },
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
    <Dialog open={isCreateDatasetOpen} onOpenChange={(open) => { setCreateDatasetOpen(open); if (!open) resetForm(); }}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Create Governed Dataset</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Establish an application-scoped dataset to enforce transfer integrity controls.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

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
              placeholder="e.g. Daily Settlement File"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-9 text-xs"
              required
            />
            <span className="text-[11px] text-muted-foreground mt-1 block">
              Unique identifier scoped within this application.
            </span>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Business Context & Purpose <span className="text-rose-500">*</span>
            </label>
            <Textarea
              placeholder="Describe the operational business purpose, data semantics, and upstream generation cadence..."
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
              Technical Documentation / Schema Notes (Optional)
            </label>
            <Textarea
              placeholder="Markdown formatted schema, table pointers, or field specifications..."
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
              onClick={() => { setCreateDatasetOpen(false); resetForm(); }}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={createMutation.isPending}
              className="text-xs font-semibold"
            >
              {createMutation.isPending ? "Creating..." : "Create Dataset"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
