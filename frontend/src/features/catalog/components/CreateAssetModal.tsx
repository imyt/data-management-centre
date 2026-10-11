import React, { useState, useMemo, useEffect } from "react";
import { X, BookOpen, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AssetType, Domain } from "@/api/client";
import { createAssetHeadAndInitialDraftApiV1AssetsPostMutation } from "@/api/client";
import { DynamicAttributeForm } from "./DynamicAttributeForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface CreateAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  domains: Domain[];
  assetTypes: AssetType[];
  onAssetCreated?: () => void;
}

export const CreateAssetModal: React.FC<CreateAssetModalProps> = ({
  isOpen,
  onClose,
  domains,
  assetTypes,
  onAssetCreated,
}) => {
  const [name, setName] = useState("");
  const [domainId, setDomainId] = useState(domains[0]?.id || "");
  const [assetTypeId, setAssetTypeId] = useState(assetTypes[0]?.id || "");
  const [description, setDescription] = useState("");
  const [attributesPayload, setAttributesPayload] = useState<Record<string, any>>({});
  const [attributeErrors, setAttributeErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  // Sync selected domain / assetType defaults when lists update
  useEffect(() => {
    if (!domainId && domains[0]?.id) {
      setDomainId(domains[0].id);
    }
  }, [domains, domainId]);

  useEffect(() => {
    if (!assetTypeId && assetTypes[0]?.id) {
      setAssetTypeId(assetTypes[0].id);
    }
  }, [assetTypes, assetTypeId]);

  const selectedAssetType = useMemo(() => {
    return assetTypes.find((t) => t.id === assetTypeId) || assetTypes[0] || null;
  }, [assetTypes, assetTypeId]);

  // Reset or initialize default attribute values whenever selected Asset Type changes
  useEffect(() => {
    if (selectedAssetType?.attribute_assignments) {
      const initial: Record<string, any> = {};
      for (const assignment of selectedAssetType.attribute_assignments) {
        const code = assignment.attribute_type.code;
        const dt = (assignment.attribute_type.data_type || "").toUpperCase();
        if (assignment.default_value !== undefined && assignment.default_value !== null) {
          initial[code] = assignment.default_value;
        } else if (dt === "BOOLEAN" || dt === "BOOL") {
          initial[code] = false;
        }
      }
      setAttributesPayload(initial);
      setAttributeErrors({});
    }
  }, [selectedAssetType]);

  const queryClient = useQueryClient();
  const createMutation = useMutation({
    ...createAssetHeadAndInitialDraftApiV1AssetsPostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Asset name is required");
      return;
    }

    // Validate required metamodel attributes client-side before submit
    if (selectedAssetType?.attribute_assignments) {
      const fieldErrors: Record<string, string> = {};
      for (const assignment of selectedAssetType.attribute_assignments) {
        if (assignment.is_required) {
          const code = assignment.attribute_type.code;
          const val = attributesPayload[code];
          if (
            val === undefined ||
            val === null ||
            (typeof val === "string" && !val.trim()) ||
            (Array.isArray(val) && val.length === 0)
          ) {
            fieldErrors[code] = `${assignment.attribute_type.name} is required`;
          }
        }
      }
      if (Object.keys(fieldErrors).length > 0) {
        setAttributeErrors(fieldErrors);
        setError("Please complete all required metamodel attributes.");
        return;
      }
    }

    setError(null);
    setAttributeErrors({});

    try {
      await createMutation.mutateAsync({
        body: {
          domain_id: domainId || domains[0]?.id,
          asset_type_id: assetTypeId || assetTypes[0]?.id,
          name: name.trim(),
          description_markdown: description,
          attributes_payload: attributesPayload,
        },
      });
      setName("");
      setDescription("");
      setAttributesPayload({});
      onAssetCreated?.();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to propose asset");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs select-none p-4">
      <div className="bg-card border border-border w-full max-w-lg max-h-[90vh] rounded-lg shadow-2xl overflow-hidden flex flex-col animate-in fade-in-0 zoom-in-95 duration-150">
        {/* Header */}
        <div className="h-11 px-4 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-4 h-4 text-primary" />
            <span className="font-semibold text-xs text-foreground">Propose New Governance Asset</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-4 space-y-3.5 overflow-y-auto flex-1">
          {error && (
            <div className="p-2 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded">
              {error}
            </div>
          )}

          {/* Name */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Asset Name *</label>
            <Input
              type="text"
              required
              placeholder="e.g. Adjusted EBITDA, Customer Tax Identification Number"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-xs"
            />
          </div>

          {/* Domain & Type Selects */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Domain Scope *</label>
              <select
                value={domainId || domains[0]?.id || ""}
                onChange={(e) => setDomainId(e.target.value)}
                className="w-full px-2.5 py-1 bg-muted/30 border border-input rounded-md text-xs text-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/30 cursor-pointer h-7"
              >
                {domains.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Metamodel Type *</label>
              <select
                value={assetTypeId || assetTypes[0]?.id || ""}
                onChange={(e) => setAssetTypeId(e.target.value)}
                className="w-full px-2.5 py-1 bg-muted/30 border border-input rounded-md text-xs text-foreground outline-none focus:border-ring focus:ring-2 focus:ring-ring/30 cursor-pointer h-7"
              >
                {assetTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Definition (Markdown)</label>
            <Textarea
              rows={3}
              placeholder="Detailed semantic definition and enterprise context..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="font-mono text-[11px] text-xs"
            />
          </div>

          {/* Dynamic Metamodel Attributes */}
          <div className="pt-2 border-t border-border">
            <DynamicAttributeForm
              assetType={selectedAssetType}
              values={attributesPayload}
              onChange={(newVals) => {
                setAttributesPayload(newVals);
                setAttributeErrors({});
              }}
              errors={attributeErrors}
              disabled={createMutation.isPending}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-border">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="h-8 text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={createMutation.isPending}
              className="h-8 text-xs font-medium gap-1.5"
            >
              {createMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{createMutation.isPending ? "Submitting..." : "Propose Asset"}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
