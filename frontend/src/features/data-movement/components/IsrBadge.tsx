import React from "react";
import { Badge } from "@/components/ui/badge";
import type { IsrClassificationEnum } from "@/api/generated";

interface IsrBadgeProps {
  classification: IsrClassificationEnum;
}

export const IsrBadge: React.FC<IsrBadgeProps> = ({ classification }) => {
  switch (classification) {
    case "HIGHLY_RESTRICTED":
      return (
        <Badge variant="destructive" className="font-mono text-[10px] tracking-wide bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30">
          HIGHLY RESTRICTED
        </Badge>
      );
    case "RESTRICTED":
      return (
        <Badge variant="destructive" className="font-mono text-[10px] tracking-wide bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
          RESTRICTED
        </Badge>
      );
    case "INTERNAL":
      return (
        <Badge variant="soft" className="font-mono text-[10px] tracking-wide">
          INTERNAL
        </Badge>
      );
    case "PUBLIC":
    default:
      return (
        <Badge variant="outline" className="font-mono text-[10px] tracking-wide text-emerald-600 dark:text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
          PUBLIC
        </Badge>
      );
  }
};
