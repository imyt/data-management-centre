import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { EyeOff, Globe, Plus, Trash2, UserCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { workbenchApi } from "../api/workbenchApi";
import { useWorkbenchUiStore } from "../stores/workbench.store";

interface PrivacyUsageViewProps {
  appHeadId: string;
}

export const PrivacyUsageView: React.FC<PrivacyUsageViewProps> = ({ appHeadId }) => {
  const queryClient = useQueryClient();
  const { setCreateEntitlementModalOpen } = useWorkbenchUiStore();

  const { data: columns = [] } = useQuery({
    queryKey: ["physical-columns", appHeadId],
    queryFn: () => workbenchApi.listColumns(appHeadId),
    enabled: !!appHeadId,
  });

  const { data: entitlements = [] } = useQuery({
    queryKey: ["usage-entitlements", appHeadId],
    queryFn: () => workbenchApi.listEntitlements(appHeadId),
    enabled: !!appHeadId,
  });

  const updateMaskingMutation = useMutation({
    mutationFn: ({ columnId, maskingStrategy, isPii, isr }: { columnId: string; maskingStrategy: string; isPii: boolean; isr: string }) =>
      workbenchApi.updateColumnClassification(columnId, {
        is_pii: isPii,
        masking_strategy: maskingStrategy,
        isr_classification: isr,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["physical-columns", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-issues", appHeadId] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (entitlementId: string) => workbenchApi.revokeEntitlement(entitlementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usage-entitlements", appHeadId] });
      queryClient.invalidateQueries({ queryKey: ["workbench-summary", appHeadId] });
    },
  });

  return (
    <div className="space-y-8">
      {/* SECTION 1: Consumer Usage Entitlements & Geo-Fencing */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-foreground tracking-tight flex items-center gap-2">
              <Globe className="w-4 h-4 text-primary" />
              <span>Consumer Usage Entitlements & Geo-Fencing Boundaries</span>
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Control downstream consumption rights. Authorize third-party systems under purpose-bound access and geographic boundaries.
            </p>
          </div>

          <Button
            size="sm"
            onClick={() => setCreateEntitlementModalOpen(true)}
            className="text-xs h-8 gap-1.5 font-semibold"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Authorize Consumer App</span>
          </Button>
        </div>

        <Card className="border-border bg-card">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs font-semibold">Consumer Application</TableHead>
                  <TableHead className="text-xs font-semibold">Authorized Purpose</TableHead>
                  <TableHead className="text-xs font-semibold">Geo-Fencing Boundaries</TableHead>
                  <TableHead className="text-xs font-semibold">Expires</TableHead>
                  <TableHead className="text-xs font-semibold">Status</TableHead>
                  <TableHead className="text-xs font-semibold text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entitlements.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-6 text-xs text-muted-foreground">
                      No consumer applications authorized yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  entitlements.map((ent) => (
                    <TableRow key={ent.id} className="text-xs">
                      <TableCell className="font-semibold text-foreground">
                        <div className="flex items-center gap-2">
                          <UserCheck className="w-3.5 h-3.5 text-primary" />
                          <span>{ent.consumer_app_name}</span>
                          <span className="font-mono text-[10px] text-muted-foreground">({ent.consumer_system_id})</span>
                        </div>
                      </TableCell>

                      <TableCell className="text-muted-foreground max-w-xs truncate">
                        {ent.authorized_purpose}
                      </TableCell>

                      <TableCell>
                        <div className="flex items-center gap-1 flex-wrap">
                          {ent.allowed_geo_regions.map((geo) => (
                            <Badge key={geo} variant="outline" className="text-[10px] font-mono bg-muted/50">
                              {geo}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>

                      <TableCell className="font-mono text-muted-foreground">
                        {new Date(ent.expires_at).toLocaleDateString()}
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant={ent.is_active ? "outline" : "secondary"}
                          className={`text-[10px] font-mono ${
                            ent.is_active
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                              : "text-muted-foreground"
                          }`}
                        >
                          {ent.is_active ? "ACTIVE" : "REVOKED"}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-right">
                        {ent.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={revokeMutation.isPending}
                            onClick={() => revokeMutation.mutate(ent.id)}
                            className="h-7 text-xs text-red-600 hover:text-red-700 hover:bg-red-500/10 gap-1"
                          >
                            <Trash2 className="w-3 h-3" />
                            Revoke
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* SECTION 2: Atomic Column Privacy & Masking Policies */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-foreground tracking-tight flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-primary" />
            <span>Atomic Column Privacy & Dynamic Masking Policies</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure field-level masking rules (Tokenization, SHA-256 Hashing, Partial Redaction) for sensitive PII columns.
          </p>
        </div>

        <Card className="border-border bg-card">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs font-semibold">Table / Column</TableHead>
                  <TableHead className="text-xs font-semibold">Data Type</TableHead>
                  <TableHead className="text-xs font-semibold">PII Indicator</TableHead>
                  <TableHead className="text-xs font-semibold">ISR Classification</TableHead>
                  <TableHead className="text-xs font-semibold">Dynamic Masking Strategy</TableHead>
                  <TableHead className="text-xs font-semibold">Business Term</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {columns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-6 text-xs text-muted-foreground">
                      No harvested physical columns found. Run a schema harvest first.
                    </TableCell>
                  </TableRow>
                ) : (
                  columns.map((col) => {
                    const isSensitiveWithoutMask = col.is_pii && col.masking_strategy === "NONE";

                    return (
                      <TableRow
                        key={col.id}
                        className={`text-xs ${isSensitiveWithoutMask ? "bg-amber-500/5 hover:bg-amber-500/10" : ""}`}
                      >
                        <TableCell className="font-medium text-foreground">
                          <div className="flex items-center gap-1.5">
                            <span className="text-muted-foreground font-mono">{col.table_name}.</span>
                            <span className="font-mono font-bold">{col.column_name}</span>
                          </div>
                        </TableCell>

                        <TableCell className="font-mono text-muted-foreground">
                          {col.data_type}
                        </TableCell>

                        <TableCell>
                          {col.is_pii ? (
                            <Badge variant="destructive" className="text-[10px] font-mono">
                              PII
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">—</span>
                          )}
                        </TableCell>

                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`text-[10px] font-mono ${
                              col.isr_classification === "HIGHLY_RESTRICTED"
                                ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                                : col.isr_classification === "RESTRICTED"
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {col.isr_classification}
                          </Badge>
                        </TableCell>

                        <TableCell className="w-56">
                          <Select
                            value={col.masking_strategy}
                            onValueChange={(val) =>
                              updateMaskingMutation.mutate({
                                columnId: col.id,
                                maskingStrategy: val,
                                isPii: col.is_pii,
                                isr: col.isr_classification,
                              })
                            }
                          >
                            <SelectTrigger className="h-7 text-xs bg-background">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="NONE" className="text-xs">
                                NONE (Plaintext)
                              </SelectItem>
                              <SelectItem value="FULL_REDACTION" className="text-xs font-medium">
                                FULL_REDACTION (***)
                              </SelectItem>
                              <SelectItem value="PARTIAL_MASK" className="text-xs font-medium">
                                PARTIAL_MASK (****-1234)
                              </SelectItem>
                              <SelectItem value="TOKENIZE" className="text-xs font-medium">
                                TOKENIZE (Format Preserving)
                              </SelectItem>
                              <SelectItem value="HASH_SHA256" className="text-xs font-medium">
                                HASH_SHA256 (Cryptographic Digest)
                              </SelectItem>
                            </SelectContent>
                          </Select>
                        </TableCell>

                        <TableCell className="text-muted-foreground truncate max-w-xs">
                          {col.business_term_name || <span className="italic text-muted-foreground/60">Unlinked</span>}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
