import React from "react";
import { ArrowRightLeft, Database } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ApplicationProfileBanner } from "./components/ApplicationProfileBanner";
import { DatasetsTable } from "./components/DatasetsTable";
import { IntegrationsList } from "./components/IntegrationsList";
import { CreateDatasetModal } from "./components/CreateDatasetModal";
import { EditDatasetModal } from "./components/EditDatasetModal";
import { DeleteSafetyModal } from "./components/DeleteSafetyModal";
import { BindDatasetModal } from "./components/BindDatasetModal";
import { DeclareIntegrityPatternModal } from "./components/DeclareIntegrityPatternModal";
import { StewardVerificationModal } from "./components/StewardVerificationModal";
import { useDataMovementUiStore } from "./stores/data-movement.store";

export const DataMovementHub: React.FC = () => {
  const { activeTab, setActiveTab } = useDataMovementUiStore();

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* Top Banner: Mastered Application System of Record Profile */}
      <ApplicationProfileBanner />

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 max-w-7xl w-full mx-auto space-y-6">
        <Tabs
          value={activeTab}
          onValueChange={(val) => setActiveTab(val as "integrations" | "datasets" | "compliance")}
          className="space-y-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-3">
            <TabsList className="h-9 p-1 bg-muted/60">
              <TabsTrigger
                value="integrations"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <ArrowRightLeft className="w-3.5 h-3.5" />
                Integrations & Data Movements
              </TabsTrigger>
              <TabsTrigger
                value="datasets"
                className="text-xs font-semibold gap-2 data-[state=active]:bg-background"
              >
                <Database className="w-3.5 h-3.5" />
                Datasets Repository
              </TabsTrigger>
            </TabsList>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                ITSM Sync: Active
              </span>
            </div>
          </div>

          <TabsContent value="integrations" className="space-y-4 focus-visible:outline-none">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-foreground tracking-tight">
                  Synchronized Integrations & Integrity Contracts
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Directional CMDB integrations enriched with governed datasets, transfer integrity patterns, and SLA certifications.
                </p>
              </div>
            </div>
            <IntegrationsList />
          </TabsContent>

          <TabsContent value="datasets" className="space-y-4 focus-visible:outline-none">
            <div>
              <h2 className="text-base font-bold text-foreground tracking-tight">
                Application-Scoped Datasets
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Maintain lifecycle ownership of datasets, Information Security Risk classifications, and domain tags.
              </p>
            </div>
            <DatasetsTable />
          </TabsContent>
        </Tabs>
      </div>

      {/* Global Modals */}
      <CreateDatasetModal />
      <EditDatasetModal />
      <DeleteSafetyModal />
      <BindDatasetModal />
      <DeclareIntegrityPatternModal />
      <StewardVerificationModal />
    </div>
  );
};
