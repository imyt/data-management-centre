import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, Lock, Plus, Clock, Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

interface StorageControlViewProps {
  appHeadId: string;
}

export const StorageControlView: React.FC<StorageControlViewProps> = ({ appHeadId }) => {
  const queryClient = useQueryClient();
  const { setCreateStorageModalOpen } = useWorkbenchUiStore();

  const { data: storages = [], isLoading } = useQuery({
    queryKey: ["storage-controls", appHeadId],
    queryFn: () => workbenchApi.listStorageControls(appHeadId),
    enabled: !!appHeadId,
  });

  const legalHoldMutation = useMutation({
    mutationFn: ({ storageId, active }: { storageId: string; active: boolean }) =>
      workbenchApi.toggleLegalHold(storageId, active, active ? "Application Owner manual legal hold invocation" : null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage-controls", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", appHeadId] });
    },
  });

  const attestPurgeMutation = useMutation({
    mutationFn: (storageId: string) =>
      workbenchApi.attestPurge(storageId, "Direct verification in Storage & Retention control plane"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage-controls", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues", appHeadId] });
    },
  });

  if (isLoading) {
    return <div className="h-64 bg-muted/20 animate-pulse rounded-xl" />;
  }

  return (
    <div className="space-y-6">
      {/* Plane Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-foreground tracking-tight">
            Storage Repositories & Data Retention Controls
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage physical database/bucket encryption, retention TTL windows, cryptographic purges, and legal holds.
          </p>
        </div>

        <Button
          size="sm"
          onClick={() => setCreateStorageModalOpen(true)}
          className="text-xs h-8 gap-1.5 font-semibold"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Register Repository</span>
        </Button>
      </div>

      {/* Repositories Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {storages.map((storage) => {
          const isOverdue = storage.is_purge_overdue;

          return (
            <Card
              key={storage.id}
              className={`transition-all border ${
                storage.legal_hold_active
                  ? "border-primary/50 bg-primary/5"
                  : isOverdue
                  ? "border-red-500/40 bg-red-500/5"
                  : "border-border bg-card"
              }`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                      <Database className="w-4 h-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-bold font-mono tracking-tight">
                        {storage.storage_name}
                      </CardTitle>
                      <CardDescription className="text-xs font-sans">
                        Platform: <span className="font-semibold text-foreground">{storage.storage_type}</span>
                      </CardDescription>
                    </div>
                  </div>

                  <Badge
                    variant={isOverdue ? "destructive" : "secondary"}
                    className="text-[10px] font-mono"
                  >
                    {isOverdue ? "PURGE OVERDUE" : "HEALTHY"}
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-0 text-xs">
                {/* Legal Hold Alert Banner if active */}
                {storage.legal_hold_active && (
                  <div className="bg-primary/15 border border-primary/30 text-primary p-2.5 rounded-lg flex items-center gap-2 font-medium">
                    <Scale className="w-4 h-4 shrink-0" />
                    <span>Legal Hold Active: Automated retention purges are legally suspended.</span>
                  </div>
                )}

                {/* Configuration Specs */}
                <div className="grid grid-cols-2 gap-3 bg-muted/40 p-3 rounded-lg border border-border/60">
                  <div>
                    <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <Lock className="w-3 h-3" />
                      Encryption at Rest
                    </div>
                    <div className="font-semibold text-foreground mt-0.5">
                      {storage.encryption_algorithm}
                    </div>
                    {storage.kms_key_arn && (
                      <div className="text-[10px] font-mono text-muted-foreground truncate max-w-[180px]" title={storage.kms_key_arn}>
                        {storage.kms_key_arn}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Retention TTL Window
                    </div>
                    <div className="font-semibold text-foreground mt-0.5">
                      {storage.retention_period_days} Days
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      Mechanism: {storage.purge_mechanism}
                    </div>
                  </div>
                </div>

                {/* Purge Attestation Status */}
                <div className="flex items-center justify-between border-t border-border/60 pt-3 text-xs">
                  <div>
                    <div className="text-muted-foreground text-[11px]">Last Purge Attestation:</div>
                    <div className="font-medium text-foreground">
                      {storage.last_purge_attestation_at
                        ? `${new Date(storage.last_purge_attestation_at).toLocaleDateString()} (${storage.days_since_purge}d ago)`
                        : "Never Attested"}
                    </div>
                  </div>

                  {isOverdue && !storage.legal_hold_active && (
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={attestPurgeMutation.isPending}
                      onClick={() => attestPurgeMutation.mutate(storage.id)}
                      className="h-7 text-xs px-2.5 font-bold"
                    >
                      Attest Purge Now
                    </Button>
                  )}
                </div>

                {/* Legal Hold Toggle Switch */}
                <div className="flex items-center justify-between border-t border-border/60 pt-3">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <Scale className="w-3.5 h-3.5 text-primary" />
                      <span>Legal Hold Freeze</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Freezes automated deletion cycles during litigation or compliance audits
                    </div>
                  </div>

                  <Switch
                    checked={storage.legal_hold_active}
                    disabled={legalHoldMutation.isPending}
                    onCheckedChange={(checked) =>
                      legalHoldMutation.mutate({ storageId: storage.id, active: checked })
                    }
                  />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
