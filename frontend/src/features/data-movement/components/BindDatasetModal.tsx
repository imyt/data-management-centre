import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, ShieldCheck, AlertCircle } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listApplicationDatasetsOptions,
  bindScopeMutation,
} from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

export const BindDatasetModal: React.FC = () => {
  const { bindingIntegrationId, setBindingIntegrationId, selectedAppHeadId } =
    useDataMovementUiStore();
  const queryClient = useQueryClient();

  const [selectedDatasetId, setSelectedDatasetId] = React.useState<string>("");
  const [retentionDays, setRetentionDays] = React.useState<number>(90);
  const [encryptionInTransit, setEncryptionInTransit] = React.useState<boolean>(true);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Fetch datasets for current application
  const { data: datasets = [] } = useQuery({
    ...listApplicationDatasetsOptions({
      path: { app_head_id: selectedAppHeadId || "" },
    }),
    enabled: Boolean(selectedAppHeadId && bindingIntegrationId),
  });

  const bindMutation = useMutation({
    ...bindScopeMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setBindingIntegrationId(null);
      setSelectedDatasetId("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to bind dataset to integration.");
    },
  });

  const handleBind = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bindingIntegrationId || !selectedDatasetId) {
      setErrorMessage("Please select a dataset to bind.");
      return;
    }

    bindMutation.mutate({
      path: { integration_id: bindingIntegrationId },
      body: {
        data_set_id: selectedDatasetId,
        retention_period_days: retentionDays || 90,
        encryption_in_transit: encryptionInTransit,
      },
    });
  };

  const handleClose = () => {
    setBindingIntegrationId(null);
    setSelectedDatasetId("");
    setErrorMessage(null);
  };

  return (
    <Dialog open={Boolean(bindingIntegrationId)} onOpenChange={(open: boolean) => !open && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Bind Governed Dataset</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Associate an application-scoped dataset to this technical data movement integration.
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

        <form onSubmit={handleBind} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="dataset-select" className="text-xs font-semibold">
              Select Application Dataset *
            </Label>
            <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
              <SelectTrigger id="dataset-select" className="text-xs h-9">
                <SelectValue placeholder="Choose a governed dataset..." />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id} className="text-xs">
                    {ds.name} ({ds.isr_classification || "INTERNAL"})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Datasets must be mastered within this application before binding.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="retention-days" className="text-xs font-semibold">
              Retention Period (Days)
            </Label>
            <Input
              id="retention-days"
              type="number"
              min={1}
              max={3650}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
              className="text-xs h-9"
            />
            <p className="text-[11px] text-muted-foreground">
              Duration transferred payload data is retained in staging/transit buffers.
            </p>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20">
            <div className="space-y-0.5">
              <Label htmlFor="transit-encryption" className="text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                Encryption in Transit Required
              </Label>
              <p className="text-[11px] text-muted-foreground">
                Enforces TLS 1.3 / mTLS transport encryption for this dataset.
              </p>
            </div>
            <Switch
              id="transit-encryption"
              checked={encryptionInTransit}
              onCheckedChange={setEncryptionInTransit}
            />
          </div>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" size="sm" onClick={handleClose} className="h-8 text-xs">
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={bindMutation.isPending || !selectedDatasetId}
              className="h-8 text-xs font-semibold shadow-xs"
            >
              {bindMutation.isPending ? "Binding..." : "Bind Dataset"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
