import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe, CheckCircle2 } from "lucide-react";
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
import { listApplicationsOptions } from "@/api/client";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

export const CreateEntitlementModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { isCreateEntitlementModalOpen, setCreateEntitlementModalOpen, selectedAppHeadId } = useWorkbenchUiStore();

  const { data: applications = [] } = useQuery({
    ...listApplicationsOptions(),
    enabled: isCreateEntitlementModalOpen,
  });

  const [consumerAppId, setConsumerAppId] = useState("");
  const [purpose, setPurpose] = useState("");
  const [regions, setRegions] = useState<string[]>(["US", "EU"]);
  const [durationDays, setDurationDays] = useState("365");

  // Filter out the current application from the consumer candidates
  const otherApps = applications.filter((a) => a.asset_head_id !== selectedAppHeadId);

  const mutation = useMutation({
    mutationFn: () =>
      workbenchApi.createEntitlement({
        app_head_id: selectedAppHeadId!,
        consumer_app_head_id: consumerAppId,
        authorized_purpose: purpose,
        allowed_geo_regions: regions,
        duration_days: parseInt(durationDays, 10),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usage-entitlements", selectedAppHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", selectedAppHeadId] });
      setCreateEntitlementModalOpen(false);
      setPurpose("");
    },
  });

  const toggleRegion = (reg: string) => {
    setRegions((prev) => (prev.includes(reg) ? prev.filter((r) => r !== reg) : [...prev, reg]));
  };

  return (
    <Dialog open={isCreateEntitlementModalOpen} onOpenChange={setCreateEntitlementModalOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Globe className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold">Authorize Consumer Application</DialogTitle>
              <DialogDescription className="text-xs">
                Grant downstream data access under an explicit business purpose and regional boundaries.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-3.5 py-2 text-xs">
          <div className="space-y-1">
            <Label className="text-xs font-semibold">Select Consumer Application</Label>
            <Select value={consumerAppId} onValueChange={setConsumerAppId}>
              <SelectTrigger className="h-8 text-xs bg-background">
                <SelectValue placeholder="Select consuming application..." />
              </SelectTrigger>
              <SelectContent>
                {otherApps.map((a) => (
                  <SelectItem key={a.asset_head_id} value={a.asset_head_id} className="text-xs">
                    <span className="font-medium">{a.itsm_system_name}</span>{" "}
                    <span className="text-[10px] font-mono text-muted-foreground">({a.itsm_system_id})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs font-semibold">Authorized Business Purpose</Label>
            <Input
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="e.g. Anti-Money Laundering transaction scoring & model training"
              className="h-8 text-xs bg-background"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Allowed Geographic Regions (Geo-Fencing)</Label>
            <div className="flex items-center gap-2 flex-wrap">
              {["US", "EU", "APAC", "UK", "LATAM"].map((reg) => (
                <button
                  key={reg}
                  type="button"
                  onClick={() => toggleRegion(reg)}
                  className={`px-2.5 py-1 rounded text-xs font-mono font-medium border transition-colors ${
                    regions.includes(reg)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted/50 text-muted-foreground border-border hover:bg-muted"
                  }`}
                >
                  {reg}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs font-semibold">Authorization Period (Days)</Label>
            <Input
              type="number"
              value={durationDays}
              onChange={(e) => setDurationDays(e.target.value)}
              className="h-8 text-xs bg-background"
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" size="sm" onClick={() => setCreateEntitlementModalOpen(false)} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={mutation.isPending || !consumerAppId || !purpose || regions.length === 0}
            onClick={() => mutation.mutate()}
            className="text-xs h-8 font-bold gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? "Authorizing..." : "Grant Entitlement"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
