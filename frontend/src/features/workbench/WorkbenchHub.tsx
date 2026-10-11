import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  Database,
  EyeOff,
  Layers,
  Inbox,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { WorkbenchHeader } from "./components/WorkbenchHeader";
import { ExecutivePostureBanner } from "./components/ExecutivePostureBanner";
import { RemediationInboxView } from "./components/RemediationInboxView";
import { StorageControlView } from "./components/StorageControlView";
import { PrivacyUsageView } from "./components/PrivacyUsageView";
import { SchemaHarvestView } from "./components/SchemaHarvestView";

// Movement Components & Modals
import { IntegrationsList } from "@/features/data-movement/components/IntegrationsList";
import { DatasetsTable } from "@/features/data-movement/components/DatasetsTable";
import { CreateDatasetModal } from "@/features/data-movement/components/CreateDatasetModal";
import { EditDatasetModal } from "@/features/data-movement/components/EditDatasetModal";
import { DeleteSafetyModal } from "@/features/data-movement/components/DeleteSafetyModal";
import { BindDatasetModal } from "@/features/data-movement/components/BindDatasetModal";
import { DeclareIntegrityPatternModal } from "@/features/data-movement/components/DeclareIntegrityPatternModal";
import { StewardVerificationModal } from "@/features/data-movement/components/StewardVerificationModal";
import { useDataMovementUiStore } from "@/features/data-movement/stores/data-movement.store";

// Workbench Modals
import { RemediateIntegrityModal } from "./components/RemediateIntegrityModal";
import { RemediateDriftModal } from "./components/RemediateDriftModal";
import { RemediatePurgeModal } from "./components/RemediatePurgeModal";
import { RemediateMaskingModal } from "./components/RemediateMaskingModal";
import { ExemptionModal } from "./components/ExemptionModal";
import { CreateStorageModal } from "./components/CreateStorageModal";
import { CreateEntitlementModal } from "./components/CreateEntitlementModal";

import { useWorkbenchUiStore, type WorkbenchTab } from "./stores/workbench.store";
import { workbenchApi } from "./api/workbenchApi";

export const WorkbenchHub: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedAppHeadId, activeTab, setActiveTab } = useWorkbenchUiStore();
  const { setSelectedAppHeadId: setMovementAppId } = useDataMovementUiStore();

  // Sync movement app id with workbench app id
  React.useEffect(() => {
    if (selectedAppHeadId) {
      setMovementAppId(selectedAppHeadId);
    }
  }, [selectedAppHeadId, setMovementAppId]);

  // Query Application Governance Posture & Summary
  const {
    data: summary,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["workbench-summary", selectedAppHeadId],
    queryFn: () => workbenchApi.getSummary(selectedAppHeadId!),
    enabled: !!selectedAppHeadId,
  });

  // Query Actionable Compliance Defects
  const { data: issues = [], isLoading: isIssuesLoading } = useQuery({
    queryKey: ["workbench-issues", selectedAppHeadId],
    queryFn: () => workbenchApi.listIssues(selectedAppHeadId!),
    enabled: !!selectedAppHeadId,
  });

  const openIssuesCount = summary?.posture.open_defects ?? issues.filter((i) => i.status !== "RESOLVED").length;

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden w-full">
      {/* 1. Master Application System of Record Header Banner */}
      <WorkbenchHeader
        summary={summary}
        onRefresh={() => {
          refetch();
          queryClient.invalidateQueries({ queryKey: ["workbench-issues", selectedAppHeadId] });
        }}
        isRefreshing={isRefetching}
      />

      {/* 2. Scrollable Workbench Core */}
      <div className="flex-1 overflow-y-auto px-6 py-5 max-w-7xl w-full mx-auto space-y-6">
        {/* Executive Compliance Posture & SLA Countdown Banner */}
        <ExecutivePostureBanner summary={summary} />

        {/* 3. The 4 Unified Control Planes & Actionable Remediation Tabs */}
        <Tabs
          value={activeTab}
          onValueChange={(val) => setActiveTab(val as WorkbenchTab)}
          className="space-y-6"
        >
          <div className="border-b border-border pb-1">
            <TabsList className="h-10 p-1 bg-muted/60">
              {/* Tab 1: Action-Oriented Remediation Inbox (Default) */}
              <TabsTrigger
                value="inbox"
                className="text-xs font-bold gap-2 data-[state=active]:bg-background"
              >
                <Inbox className="w-3.5 h-3.5" />
                <span>Remediation Inbox</span>
                {openIssuesCount > 0 && (
                  <Badge
                    variant="destructive"
                    className="ml-1 px-1.5 py-0 text-[10px] font-mono h-4 font-bold"
                  >
                    {openIssuesCount}
                  </Badge>
                )}
              </TabsTrigger>

              {/* Tab 2: Control Plane 1 - Data Movement & Integrity */}
              <TabsTrigger
                value="movement"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <ArrowRightLeft className="w-3.5 h-3.5" />
                <span>Data Movement & Integrity</span>
              </TabsTrigger>

              {/* Tab 3: Control Plane 2 - Storage & Retention */}
              <TabsTrigger
                value="storage"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <Database className="w-3.5 h-3.5" />
                <span>Storage & Retention</span>
                {summary?.posture.breached_defects ? (
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                ) : null}
              </TabsTrigger>

              {/* Tab 4: Control Plane 3 - Privacy & Usage */}
              <TabsTrigger
                value="privacy"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <EyeOff className="w-3.5 h-3.5" />
                <span>Privacy & Usage</span>
              </TabsTrigger>

              {/* Tab 5: Control Plane 4 - Schema Harvesting & Drift */}
              <TabsTrigger
                value="harvest"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Schema Harvesting & Drift</span>
                {summary?.control_planes.schema_harvest.unclassified_drift ? (
                  <Badge variant="outline" className="text-[9px] font-mono border-amber-500/40 text-amber-600 bg-amber-500/10">
                    Drift
                  </Badge>
                ) : null}
              </TabsTrigger>
            </TabsList>
          </div>

          {/* TAB 1 CONTENT: REMEDIATION INBOX */}
          <TabsContent value="inbox" className="focus-visible:outline-none">
            <RemediationInboxView issues={issues} isLoading={isIssuesLoading} />
          </TabsContent>

          {/* TAB 2 CONTENT: DATA MOVEMENT & INTEGRITY */}
          <TabsContent value="movement" className="space-y-8 focus-visible:outline-none">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-foreground tracking-tight">
                    Synchronized Technical Integrations
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Directional integrations synchronized read-only from ServiceNow CMDB and certified with transfer integrity patterns.
                  </p>
                </div>
              </div>
              <IntegrationsList />
            </div>

            <div className="space-y-4 pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-foreground tracking-tight">
                    Application Datasets Repository
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Self-serviced dataset definitions authored by the Application Owner tying business context to movement conduits.
                  </p>
                </div>
              </div>
              <DatasetsTable />
            </div>
          </TabsContent>

          {/* TAB 3 CONTENT: STORAGE & RETENTION */}
          <TabsContent value="storage" className="focus-visible:outline-none">
            <StorageControlView appHeadId={selectedAppHeadId || ""} />
          </TabsContent>

          {/* TAB 4 CONTENT: PRIVACY & USAGE */}
          <TabsContent value="privacy" className="focus-visible:outline-none">
            <PrivacyUsageView appHeadId={selectedAppHeadId || ""} />
          </TabsContent>

          {/* TAB 5 CONTENT: SCHEMA HARVESTING & DRIFT */}
          <TabsContent value="harvest" className="focus-visible:outline-none">
            <SchemaHarvestView appHeadId={selectedAppHeadId || ""} />
          </TabsContent>
        </Tabs>
      </div>

      {/* 4. In-Line Remediation Modals & Workflows */}
      <RemediateIntegrityModal />
      <RemediateDriftModal />
      <RemediatePurgeModal />
      <RemediateMaskingModal />
      <ExemptionModal />
      <CreateStorageModal />
      <CreateEntitlementModal />

      {/* 5. Movement Modals */}
      <CreateDatasetModal />
      <EditDatasetModal />
      <DeleteSafetyModal />
      <BindDatasetModal />
      <DeclareIntegrityPatternModal />
      <StewardVerificationModal />
    </div>
  );
};
