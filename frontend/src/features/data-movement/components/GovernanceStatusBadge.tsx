import React from "react";
import { Badge } from "@/components/ui/badge";
import { ShieldAlert, ShieldCheck, Clock, FileWarning, Award } from "lucide-react";
import type { IntegrationGovernanceStatusEnum } from "@/api/generated";

interface GovernanceStatusBadgeProps {
  status: IntegrationGovernanceStatusEnum;
}

export const GovernanceStatusBadge: React.FC<GovernanceStatusBadgeProps> = ({ status }) => {
  switch (status) {
    case "COMPLIANT":
      return (
        <Badge className="font-mono text-[10px] tracking-wide bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-500" />
          COMPLIANT
        </Badge>
      );
    case "PENDING_VERIFICATION":
      return (
        <Badge variant="soft" className="font-mono text-[10px] tracking-wide flex items-center gap-1">
          <Clock className="w-3 h-3 text-primary animate-pulse" />
          PENDING VERIFICATION
        </Badge>
      );
    case "IN_REMEDIATION":
      return (
        <Badge className="font-mono text-[10px] tracking-wide bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 flex items-center gap-1">
          <FileWarning className="w-3 h-3 text-amber-500" />
          IN REMEDIATION
        </Badge>
      );
    case "EXEMPTION_GRANTED":
      return (
        <Badge variant="outline" className="font-mono text-[10px] tracking-wide border-primary/30 text-primary bg-primary/5 flex items-center gap-1">
          <Award className="w-3 h-3 text-primary" />
          EXEMPTION GRANTED
        </Badge>
      );
    case "UNGOVERNED":
    default:
      return (
        <Badge variant="destructive" className="font-mono text-[10px] tracking-wide bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 flex items-center gap-1">
          <ShieldAlert className="w-3 h-3 text-rose-500" />
          UNGOVERNED
        </Badge>
      );
  }
};
