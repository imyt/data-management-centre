import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Lock, ShieldAlert, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { getDatasetUsagesOptions, deleteDatasetMutation } from "@/api/client";
import { useDataMovementUiStore } from "../stores/data-movement.store";

export const DeleteSafetyModal: React.FC = () => {
  const { deletingDatasetId, setDeletingDatasetId, selectedAppHeadId } = useDataMovementUiStore();
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Pre-flight check: query blocking active integrations currently bound to this dataset
  const { data: usages = [], isLoading: isLoadingUsages } = useQuery({
    ...getDatasetUsagesOptions({
      path: {
        app_head_id: selectedAppHeadId || "",
        dataset_id: deletingDatasetId || "",
      },
    }),
    enabled: Boolean(selectedAppHeadId && deletingDatasetId),
  });

  const isBlocked = usages.length > 0;

  const deleteMutation = useMutation({
    ...deleteDatasetMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setDeletingDatasetId(null);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.body?.detail || err?.message || "Failed to delete dataset.");
    },
  });

  const handleConfirmDelete = () => {
    if (!selectedAppHeadId || !deletingDatasetId || isBlocked) return;
    deleteMutation.mutate({
      path: {
        app_head_id: selectedAppHeadId,
        dataset_id: deletingDatasetId,
      },
    });
  };

  const handleClose = () => {
    setDeletingDatasetId(null);
    setErrorMessage(null);
  };

  return (
    <AlertDialog open={Boolean(deletingDatasetId)} onOpenChange={(open: boolean) => !open && handleClose()}>
      <AlertDialogContent className="sm:max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                isBlocked
                  ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}
            >
              {isBlocked ? <Lock className="w-5 h-5" /> : <Trash2 className="w-5 h-5" />}
            </div>
            <div>
              <AlertDialogTitle className="text-base font-bold">
                {isBlocked ? "Deletion Blocked by Active Integrations" : "Archive Governed Dataset"}
              </AlertDialogTitle>
              <AlertDialogDescription className="text-xs text-muted-foreground mt-0.5">
                {isBlocked
                  ? "Referential integrity constraint prevents deletion while active integrations depend on this dataset."
                  : "Zero active integrations bound. This dataset will be soft-archived to preserve audit history."}
              </AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>

        {errorMessage && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {isLoadingUsages ? (
          <div className="py-6 text-center text-xs text-muted-foreground animate-pulse">
            Checking integration dependencies...
          </div>
        ) : isBlocked ? (
          <div className="space-y-3">
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-md text-xs text-amber-700 dark:text-amber-400">
              <div className="flex items-center gap-1.5 font-semibold">
                <ShieldAlert className="w-4 h-4 text-amber-500" />
                Referential Lock Triggered (HTTP 409 Conflict)
              </div>
              <p className="mt-1 text-[11px] leading-relaxed">
                You must unbind this dataset from all dependent integration scopes before it can be archived.
              </p>
            </div>

            <div className="text-xs font-semibold text-foreground">
              Dependent Active Integrations ({usages.length}):
            </div>
            <div className="max-h-40 overflow-y-auto divide-y divide-border border border-border rounded-md bg-muted/20">
              {usages.map((u) => (
                <div key={u.integration_id} className="p-2.5 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {u.itsm_integration_id}
                    </Badge>
                    <span className="font-medium text-foreground">{u.partner_application_name}</span>
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    {u.governance_status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-3 bg-muted/40 border border-border rounded-md text-xs text-muted-foreground">
            <p>
              Are you sure you want to archive this dataset? It has <strong>0 active integration bindings</strong>. The dataset will be marked as archived, preserving historical auditability.
            </p>
          </div>
        )}

        <AlertDialogFooter className="mt-2">
          <AlertDialogCancel onClick={handleClose} className="h-8 text-xs">
            {isBlocked ? "Close" : "Cancel"}
          </AlertDialogCancel>
          {!isBlocked && (
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              className="h-8 text-xs bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Archiving..." : "Confirm Archive"}
            </AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
