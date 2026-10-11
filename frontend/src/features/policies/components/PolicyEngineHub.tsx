import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  ShieldAlert,
  Play,
  RotateCcw,
  Plus,
  Sliders,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  Loader2,
  ArrowRightLeft,
  Database,
  Lock,
  GitCommit,
  BookOpen,
  Info,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { policyApi, type PolicyRuleItem, type CreateCustomRulePayload, type UpdatePolicyRulePayload } from "../api/policyApi";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  DATA_MOVEMENT: <ArrowRightLeft className="w-4 h-4 text-sky-500 shrink-0" />,
  STORAGE_RETENTION: <Database className="w-4 h-4 text-purple-500 shrink-0" />,
  PRIVACY_USAGE: <Lock className="w-4 h-4 text-emerald-500 shrink-0" />,
  SCHEMA_DRIFT: <GitCommit className="w-4 h-4 text-amber-500 shrink-0" />,
  CATALOG_METADATA: <BookOpen className="w-4 h-4 text-blue-500 shrink-0" />,
};

const CATEGORY_LABELS: Record<string, string> = {
  DATA_MOVEMENT: "Data Movement",
  STORAGE_RETENTION: "Storage & Retention",
  PRIVACY_USAGE: "Privacy & Usage",
  SCHEMA_DRIFT: "Schema Drift",
  CATALOG_METADATA: "Catalog Metadata",
};

export const PolicyEngineHub: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedMode, setSelectedMode] = useState<string>("ALL");

  // Modals State
  const [editingRule, setEditingRule] = useState<PolicyRuleItem | null>(null);
  const [editForm, setEditForm] = useState<UpdatePolicyRulePayload>({});
  const [editParamsJson, setEditParamsJson] = useState("{}");
  const [editError, setEditError] = useState<string | null>(null);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addForm, setAddForm] = useState<CreateCustomRulePayload>({
    rule_code: "",
    name: "",
    description: "",
    category: "CATALOG_METADATA",
    severity: "MEDIUM",
    enforcement_mode: "BLOCKING",
    default_sla_days: 14,
    target_entity_type: "ASSET",
    parameters: {},
    remediation_guidance: "",
  });
  const [addParamsJson, setAddParamsJson] = useState("{}");
  const [addError, setAddError] = useState<string | null>(null);

  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);

  // Queries
  const { data, isLoading } = useQuery({
    queryKey: ["policy-rules"],
    queryFn: () => policyApi.listRules(),
  });

  // Mutations
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      policyApi.toggleRule(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-rules"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-issues"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdatePolicyRulePayload }) =>
      policyApi.updateRule(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-rules"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-issues"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      setEditingRule(null);
      setEditError(null);
    },
    onError: (err: unknown) => {
      setEditError(err instanceof Error ? err.message : "Failed to update rule.");
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateCustomRulePayload) => policyApi.createCustomRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-rules"] });
      setIsAddModalOpen(false);
      setAddError(null);
      setAddForm({
        rule_code: "",
        name: "",
        description: "",
        category: "CATALOG_METADATA",
        severity: "MEDIUM",
        enforcement_mode: "BLOCKING",
        default_sla_days: 14,
        target_entity_type: "ASSET",
        parameters: {},
        remediation_guidance: "",
      });
      setAddParamsJson("{}");
    },
    onError: (err: unknown) => {
      setAddError(err instanceof Error ? err.message : "Failed to create custom rule.");
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => policyApi.resetDefaults(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-rules"] });
      setIsResetConfirmOpen(false);
      setScanResult("Policy rules reset to baseline enterprise standards.");
    },
  });

  const evaluateMutation = useMutation({
    mutationFn: () => policyApi.evaluatePolicies(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["compliance-issues"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary"] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues"] });
      setScanResult(
        `Policy scan executed successfully: ${res.new_issues_count} new anomalies identified, ${res.existing_issues_count} active breaches verified.`
      );
    },
    onError: (err: unknown) => {
      setScanResult(err instanceof Error ? err.message : "Failed to run scan.");
    },
  });

  // Filtered Rules
  const allRules = data?.rules || [];
  const filteredRules = useMemo(() => {
    return allRules.filter((r) => {
      const matchesSearch =
        searchQuery.trim() === "" ||
        r.rule_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCat =
        selectedCategory === "ALL" || r.category === selectedCategory;

      const matchesMode =
        selectedMode === "ALL" ||
        (selectedMode === "BLOCKING" && r.is_enabled && r.enforcement_mode === "BLOCKING") ||
        (selectedMode === "ADVISORY" && r.is_enabled && r.enforcement_mode === "ADVISORY") ||
        (selectedMode === "DISABLED" && (!r.is_enabled || r.enforcement_mode === "DISABLED"));

      return matchesSearch && matchesCat && matchesMode;
    });
  }, [allRules, searchQuery, selectedCategory, selectedMode]);

  // Handlers for modal
  const handleOpenEdit = (rule: PolicyRuleItem) => {
    setEditingRule(rule);
    setEditForm({
      name: rule.name,
      description: rule.description,
      enforcement_mode: rule.enforcement_mode,
      severity: rule.severity,
      default_sla_days: rule.default_sla_days,
      is_enabled: rule.is_enabled,
      remediation_guidance: rule.remediation_guidance || "",
    });
    setEditParamsJson(JSON.stringify(rule.parameters, null, 2));
    setEditError(null);
  };

  const handleSaveEdit = () => {
    if (!editingRule) return;
    try {
      const parsedParams = JSON.parse(editParamsJson);
      updateMutation.mutate({
        id: editingRule.id,
        payload: {
          ...editForm,
          parameters: parsedParams,
        },
      });
    } catch {
      setEditError("Rule Parameters must be valid JSON.");
    }
  };

  const handleCreateRule = () => {
    if (!addForm.rule_code.trim()) {
      setAddError("Rule Code is required (e.g. DATA_RET_001).");
      return;
    }
    if (!addForm.name.trim()) {
      setAddError("Rule Name is required.");
      return;
    }
    try {
      const parsedParams = JSON.parse(addParamsJson);
      createMutation.mutate({
        ...addForm,
        rule_code: addForm.rule_code.trim().toUpperCase(),
        parameters: parsedParams,
      });
    } catch {
      setAddError("Rule Parameters must be valid JSON.");
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-background text-foreground p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">Governance Policy Engine</h1>
            <Badge variant="outline" className="font-mono text-xs">
              Configurable Metamodel
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Centrally manage rule definitions, severity gates, SLA timers, and enforcement modes across the 4 Control Planes.
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsResetConfirmOpen(true)}
            disabled={resetMutation.isPending}
            className="text-xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1 text-muted-foreground" />
            Reset to Baseline
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsAddModalOpen(true)}
            className="text-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 mr-1 text-primary" />
            Add Custom Rule
          </Button>

          <Button
            size="sm"
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="text-xs font-semibold shadow-xs cursor-pointer"
          >
            {evaluateMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                Evaluating Policies...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                Run Policy Scan
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Scan Feedback Banner */}
      {scanResult && (
        <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg flex items-center justify-between text-xs text-foreground animate-in fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
            <span>{scanResult}</span>
          </div>
          <button
            onClick={() => setScanResult(null)}
            className="text-muted-foreground hover:text-foreground text-xs p-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
        <Card className="shadow-2xs">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Total Policies
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono">
              {data?.summary.total_rules || 0}
            </span>
            <span className="text-[11px] text-muted-foreground">Registered</span>
          </CardContent>
        </Card>

        <Card className="shadow-2xs">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Active & Enforced
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {data?.summary.enabled_rules || 0}
            </span>
            <span className="text-[11px] text-emerald-600 font-semibold">Active</span>
          </CardContent>
        </Card>

        <Card className="shadow-2xs">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Blocking Gates
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-rose-600 dark:text-rose-400">
              {data?.summary.blocking_rules || 0}
            </span>
            <span className="text-[11px] text-rose-500 font-semibold">Hard Gates</span>
          </CardContent>
        </Card>

        <Card className="shadow-2xs">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Advisory Policies
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-amber-600 dark:text-amber-400">
              {data?.summary.advisory_rules || 0}
            </span>
            <span className="text-[11px] text-amber-500 font-semibold">Warnings</span>
          </CardContent>
        </Card>

        <Card className="shadow-2xs col-span-2 sm:col-span-4 lg:col-span-1">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Disabled Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-muted-foreground">
              {data?.summary.disabled_rules || 0}
            </span>
            <span className="text-[11px] text-muted-foreground font-semibold">Bypassed</span>
          </CardContent>
        </Card>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-card border border-border rounded-lg shadow-2xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by rule code, name, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded-md border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {/* Category Filter */}
          <div className="flex items-center space-x-1 text-xs">
            <Filter className="w-3 h-3 text-muted-foreground" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-xs px-2 py-1.5 rounded-md border border-border bg-background cursor-pointer"
            >
              <option value="ALL">All Categories</option>
              <option value="DATA_MOVEMENT">Data Movement</option>
              <option value="STORAGE_RETENTION">Storage & Retention</option>
              <option value="PRIVACY_USAGE">Privacy & Usage</option>
              <option value="SCHEMA_DRIFT">Schema Drift</option>
              <option value="CATALOG_METADATA">Catalog Metadata</option>
            </select>
          </div>

          {/* Mode Filter */}
          <select
            value={selectedMode}
            onChange={(e) => setSelectedMode(e.target.value)}
            className="text-xs px-2 py-1.5 rounded-md border border-border bg-background cursor-pointer"
          >
            <option value="ALL">All Postures</option>
            <option value="BLOCKING">Blocking Only</option>
            <option value="ADVISORY">Advisory Only</option>
            <option value="DISABLED">Disabled Only</option>
          </select>
        </div>
      </div>

      {/* Rules Grid / List */}
      {isLoading ? (
        <div className="py-20 text-center text-muted-foreground flex flex-col items-center justify-center space-y-2">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-xs">Loading governance policy rules...</span>
        </div>
      ) : filteredRules.length === 0 ? (
        <div className="py-16 text-center text-xs text-muted-foreground border border-dashed border-border rounded-lg p-6">
          <ShieldAlert className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-60" />
          <p className="font-semibold text-foreground">No matching policy rules found.</p>
          <p className="text-[11px] mt-1">Try adjusting your search criteria or category filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredRules.map((rule) => {
            const isEnabled = rule.is_enabled && rule.enforcement_mode !== "DISABLED";
            const isBlocking = rule.enforcement_mode === "BLOCKING";

            return (
              <Card
                key={rule.id}
                className={`transition-all shadow-2xs ${
                  !isEnabled
                    ? "opacity-60 bg-muted/30 border-dashed"
                    : isBlocking
                    ? "border-border hover:border-primary/40"
                    : "border-border hover:border-amber-500/40"
                }`}
              >
                <CardContent className="p-4 flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Left: Info */}
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="font-mono font-bold text-xs bg-muted px-2 py-0.5 rounded border border-border text-foreground">
                        {rule.rule_code}
                      </span>

                      <div className="flex items-center space-x-1 text-xs font-semibold text-foreground">
                        {CATEGORY_ICONS[rule.category] || <Info className="w-4 h-4" />}
                        <span>{rule.name}</span>
                      </div>

                      <Badge
                        variant="secondary"
                        className="text-[10px] font-mono px-1.5 py-0"
                      >
                        {CATEGORY_LABELS[rule.category] || rule.category}
                      </Badge>

                      <Badge
                        variant={
                          rule.severity === "CRITICAL"
                            ? "destructive"
                            : rule.severity === "HIGH"
                            ? "default"
                            : "secondary"
                        }
                        className="text-[10px] font-mono px-1.5 py-0"
                      >
                        {rule.severity}
                      </Badge>

                      {isEnabled ? (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                            isBlocking
                              ? "bg-rose-500/10 text-rose-600 border border-rose-500/20"
                              : "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                          }`}
                        >
                          {rule.enforcement_mode}
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-muted text-muted-foreground border border-border">
                          DISABLED
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {rule.description}
                    </p>

                    {/* Metadata & Parameters */}
                    <div className="flex items-center flex-wrap gap-3 pt-1 text-[11px] text-muted-foreground">
                      <div className="flex items-center space-x-1 font-mono">
                        <Clock className="w-3 h-3 text-muted-foreground" />
                        <span>SLA: {rule.default_sla_days} days</span>
                      </div>

                      <div className="flex items-center space-x-1">
                        <span className="text-[10px] font-mono uppercase bg-muted/60 px-1 py-0.5 rounded">
                          Target: {rule.target_entity_type}
                        </span>
                      </div>

                      {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                        <div className="flex items-center space-x-1">
                          <span className="text-muted-foreground">Params:</span>
                          <span className="font-mono text-[10px] bg-muted/80 px-1.5 py-0.5 rounded">
                            {JSON.stringify(rule.parameters)}
                          </span>
                        </div>
                      )}
                    </div>

                    {rule.remediation_guidance && (
                      <div className="text-[11px] text-muted-foreground/90 bg-muted/30 p-2 rounded border border-border/40 flex items-start space-x-1.5 mt-1">
                        <Info className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                        <span>
                          <strong>Guidance:</strong> {rule.remediation_guidance}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center md:flex-col justify-end gap-2 shrink-0 md:min-w-[120px]">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleOpenEdit(rule)}
                      className="text-xs w-full cursor-pointer flex items-center justify-center space-x-1"
                    >
                      <Sliders className="w-3 h-3 text-primary" />
                      <span>Configure</span>
                    </Button>

                    <Button
                      size="sm"
                      variant={isEnabled ? "secondary" : "default"}
                      onClick={() =>
                        toggleMutation.mutate({
                          id: rule.id,
                          enabled: !isEnabled,
                        })
                      }
                      disabled={toggleMutation.isPending}
                      className="text-xs w-full cursor-pointer"
                    >
                      {isEnabled ? "Disable Rule" : "Enable Rule"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Edit Rule Configuration Modal */}
      {editingRule && (
        <Dialog open={!!editingRule} onOpenChange={(open) => !open && setEditingRule(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2 text-sm font-bold">
                <Sliders className="w-4 h-4 text-primary" />
                <span>Configure Policy Rule: {editingRule.rule_code}</span>
              </DialogTitle>
            </DialogHeader>

            {editError && (
              <div className="p-2.5 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded">
                {editError}
              </div>
            )}

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="font-semibold block mb-1">Rule Name</label>
                <input
                  type="text"
                  value={editForm.name || ""}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="font-semibold block mb-1">Description</label>
                <textarea
                  value={editForm.description || ""}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  rows={2}
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Enforcement Mode</label>
                  <select
                    value={editForm.enforcement_mode || "BLOCKING"}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        enforcement_mode: e.target.value as "BLOCKING" | "ADVISORY" | "DISABLED",
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="BLOCKING">BLOCKING (Hard Gate with SLA)</option>
                    <option value="ADVISORY">ADVISORY (Warning only)</option>
                    <option value="DISABLED">DISABLED (Skip evaluation)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Severity Level</label>
                  <select
                    value={editForm.severity || "MEDIUM"}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        severity: e.target.value as "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Default Remediation SLA (Days)</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={editForm.default_sla_days || 14}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      default_sla_days: parseInt(e.target.value, 10) || 14,
                    })
                  }
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="font-semibold block mb-1">
                  Rule Parameters (JSON)
                </label>
                <textarea
                  value={editParamsJson}
                  onChange={(e) => setEditParamsJson(e.target.value)}
                  rows={3}
                  className="w-full text-xs font-mono p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  e.g., {"{"}"min_chars": 50{"}"} or {"{"}"max_purge_window_days": 90{"}"}
                </p>
              </div>

              <div>
                <label className="font-semibold block mb-1">Remediation Guidance</label>
                <textarea
                  value={editForm.remediation_guidance || ""}
                  onChange={(e) =>
                    setEditForm({ ...editForm, remediation_guidance: e.target.value })
                  }
                  rows={2}
                  placeholder="Instructions displayed to Application Owners on how to remediate violations..."
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditingRule(null)}
                className="cursor-pointer text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEdit}
                disabled={updateMutation.isPending}
                className="cursor-pointer text-xs font-semibold"
              >
                {updateMutation.isPending ? "Saving..." : "Save Configuration"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Add Custom Rule Modal */}
      {isAddModalOpen && (
        <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2 text-sm font-bold">
                <Plus className="w-4 h-4 text-primary" />
                <span>Create Custom Governance Policy Rule</span>
              </DialogTitle>
            </DialogHeader>

            {addError && (
              <div className="p-2.5 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded">
                {addError}
              </div>
            )}

            <div className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Rule Code</label>
                  <input
                    type="text"
                    placeholder="e.g. CUST_RET_001"
                    value={addForm.rule_code}
                    onChange={(e) => setAddForm({ ...addForm, rule_code: e.target.value })}
                    className="w-full text-xs p-2 rounded border border-border bg-background font-mono uppercase focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Category</label>
                  <select
                    value={addForm.category}
                    onChange={(e) =>
                      setAddForm({
                        ...addForm,
                        category: e.target.value as CreateCustomRulePayload["category"],
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="DATA_MOVEMENT">Data Movement</option>
                    <option value="STORAGE_RETENTION">Storage & Retention</option>
                    <option value="PRIVACY_USAGE">Privacy & Usage</option>
                    <option value="SCHEMA_DRIFT">Schema Drift</option>
                    <option value="CATALOG_METADATA">Catalog Metadata</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Rule Name</label>
                <input
                  type="text"
                  placeholder="e.g. Mandatory Archive Storage Tag"
                  value={addForm.name}
                  onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="font-semibold block mb-1">Description</label>
                <textarea
                  placeholder="Detailed governance policy rationale..."
                  value={addForm.description}
                  onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                  rows={2}
                  className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Enforcement Mode</label>
                  <select
                    value={addForm.enforcement_mode}
                    onChange={(e) =>
                      setAddForm({
                        ...addForm,
                        enforcement_mode: e.target.value as "BLOCKING" | "ADVISORY" | "DISABLED",
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="BLOCKING">BLOCKING (Hard Gate with SLA)</option>
                    <option value="ADVISORY">ADVISORY (Warning only)</option>
                    <option value="DISABLED">DISABLED (Skip evaluation)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Severity</label>
                  <select
                    value={addForm.severity}
                    onChange={(e) =>
                      setAddForm({
                        ...addForm,
                        severity: e.target.value as "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Default SLA (Days)</label>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={addForm.default_sla_days}
                    onChange={(e) =>
                      setAddForm({
                        ...addForm,
                        default_sla_days: parseInt(e.target.value, 10) || 14,
                      })
                    }
                    className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Target Entity Type</label>
                  <select
                    value={addForm.target_entity_type}
                    onChange={(e) => setAddForm({ ...addForm, target_entity_type: e.target.value })}
                    className="w-full text-xs p-2 rounded border border-border bg-background cursor-pointer"
                  >
                    <option value="ASSET">ASSET (Catalog entity)</option>
                    <option value="INTEGRATION">INTEGRATION (Data conduit)</option>
                    <option value="STORAGE_CONTROL">STORAGE_CONTROL (Repository)</option>
                    <option value="PHYSICAL_COLUMN">PHYSICAL_COLUMN (Database column)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Rule Parameters (JSON)</label>
                <textarea
                  value={addParamsJson}
                  onChange={(e) => setAddParamsJson(e.target.value)}
                  rows={2}
                  className="w-full text-xs font-mono p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddModalOpen(false)}
                className="cursor-pointer text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleCreateRule}
                disabled={createMutation.isPending}
                className="cursor-pointer text-xs font-semibold"
              >
                {createMutation.isPending ? "Creating..." : "Create Policy Rule"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Reset Confirmation Dialog */}
      {isResetConfirmOpen && (
        <Dialog open={isResetConfirmOpen} onOpenChange={setIsResetConfirmOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2 text-sm font-bold text-foreground">
                <RotateCcw className="w-4 h-4 text-amber-500" />
                <span>Reset to Baseline Enterprise Rules</span>
              </DialogTitle>
            </DialogHeader>

            <p className="text-xs text-muted-foreground">
              This will restore all default governance rules (MOV_001, STOR_001, PRIV_001, DRIFT_001, CAT_001-003) to their recommended enterprise baselines, severity ratings, and 14-day SLA configurations.
            </p>

            <DialogFooter className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsResetConfirmOpen(false)}
                className="cursor-pointer text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                className="cursor-pointer text-xs font-semibold"
              >
                {resetMutation.isPending ? "Resetting..." : "Confirm Reset"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
