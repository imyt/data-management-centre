import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, CheckCircle2 } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const CreateStorageModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { isCreateStorageModalOpen, setCreateStorageModalOpen, selectedAppHeadId } = useWorkbenchUiStore();

  const [storageName, setStorageName] = useState("");
  const [storageType, setStorageType] = useState("POSTGRESQL");
  const [encryptionAlgo, setEncryptionAlgo] = useState("AWS_KMS_CMK");
  const [kmsArn, setKmsArn] = useState("");
  const [retentionDays, setRetentionDays] = useState("90");
  const [purgeMech, setPurgeMech] = useState("CRYPTOGRAPHIC_ERASURE");

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.createStorageControl({
        app_head_id: selectedAppHeadId!,
        storage_name: storageName,
        storage_type: storageType,
        encryption_algorithm: encryptionAlgo,
        kms_key_arn: kmsArn || undefined,
        retention_period_days: parseInt(retentionDays, 10),
        purge_mechanism: purgeMech,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage-controls", selectedAppHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", selectedAppHeadId] });
      setCreateStorageModalOpen(false);
      setStorageName("");
      setKmsArn("");
    },
  });

  return (
    <Dialog open={isCreateStorageModalOpen} onOpenChange={setCreateStorageModalOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Register Storage Repository</DialogTitle>
              <DialogDescription className="text-xs">
                Register database or object storage and define retention compliance boundaries.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-3 py-2 text-xs">
          <div className="space-y-1">
            <Label className="text-xs font-semibold">Repository Name</Label>
            <Input
              value={storageName}
              onChange={(e) => setStorageName(e.target.value)}
              placeholder="e.g. pg-core-ledger-db or s3-customer-archive"
              className="h-8 text-xs bg-background"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Storage Technology</Label>
              <Select value={storageType} onValueChange={setStorageType}>
                <SelectTrigger className="h-8 text-xs bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="POSTGRESQL" className="text-xs">PostgreSQL</SelectItem>
                  <SelectItem value="S3_BUCKET" className="text-xs">AWS S3 Bucket</SelectItem>
                  <SelectItem value="SNOWFLAKE" className="text-xs">Snowflake</SelectItem>
                  <SelectItem value="BIGQUERY" className="text-xs">Google BigQuery</SelectItem>
                  <SelectItem value="DYNAMODB" className="text-xs">Amazon DynamoDB</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Retention TTL (Days)</Label>
              <Input
                type="number"
                value={retentionDays}
                onChange={(e) => setRetentionDays(e.target.value)}
                className="h-8 text-xs bg-background"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Encryption Algorithm</Label>
              <Select value={encryptionAlgo} onValueChange={setEncryptionAlgo}>
                <SelectTrigger className="h-8 text-xs bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AWS_KMS_CMK" className="text-xs">AWS KMS CMK</SelectItem>
                  <SelectItem value="AES_256_GCM" className="text-xs">AES-256-GCM</SelectItem>
                  <SelectItem value="DATABASE_TDE" className="text-xs">Database TDE</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Purge Mechanism</Label>
              <Select value={purgeMech} onValueChange={setPurgeMech}>
                <SelectTrigger className="h-8 text-xs bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CRYPTOGRAPHIC_ERASURE" className="text-xs">Cryptographic Erasure</SelectItem>
                  <SelectItem value="HARD_DELETE_REMOVAL" className="text-xs">Hard Delete</SelectItem>
                  <SelectItem value="PARTITION_DROP" className="text-xs">Partition Drop</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs font-semibold">KMS Key Reference ARN (Optional)</Label>
            <Input
              value={kmsArn}
              onChange={(e) => setKmsArn(e.target.value)}
              placeholder="arn:aws:kms:region:account:key/key-id"
              className="h-8 text-xs font-mono bg-background"
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={() => setCreateStorageModalOpen(false)} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending || !storageName}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Registering..." : "Register Repository"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
