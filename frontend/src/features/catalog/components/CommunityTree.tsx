import React, { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Building2,
  BookOpen,
  ShieldCheck,
  Server,
  Activity,
  Layers,
  FolderTree,
} from "lucide-react";
import type { Community, Domain } from "@/api/client";

interface CommunityTreeProps {
  communities: Community[];
  selectedDomainId: string | null;
  onSelectDomain: (domain: Domain | null) => void;
}

export const CommunityTree: React.FC<CommunityTreeProps> = ({
  communities,
  selectedDomainId,
  onSelectDomain,
}) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    root: true,
  });

  const toggle = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getDomainIcon = (type: Domain["domain_type"]) => {
    switch (type) {
      case "GLOSSARY":
        return <BookOpen className="w-3.5 h-3.5 text-blue-500" />;
      case "POLICY":
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />;
      case "SYSTEMS_REGISTER":
        return <Server className="w-3.5 h-3.5 text-purple-500" />;
      case "METRIC_STORE":
        return <Activity className="w-3.5 h-3.5 text-amber-500" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-cyan-500" />;
    }
  };

  return (
    <aside className="w-64 border-r border-border bg-card/60 flex flex-col shrink-0 select-none h-full overflow-hidden">
      {/* Sidebar Header */}
      <div className="h-9 px-3 border-b border-border flex items-center justify-between font-semibold text-xs text-muted-foreground uppercase tracking-wider">
        <div className="flex items-center space-x-1.5">
          <FolderTree className="w-3.5 h-3.5" />
          <span>Organizational Scopes</span>
        </div>
        <button
          onClick={() => onSelectDomain(null)}
          className={`text-[10px] px-1.5 py-0.5 rounded transition-colors cursor-pointer ${
            selectedDomainId === null
              ? "bg-primary text-primary-foreground font-medium"
              : "hover:bg-muted text-muted-foreground"
          }`}
        >
          All
        </button>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {communities.map((comm) => {
          const isExpanded = expanded[comm.id] ?? true;
          return (
            <div key={comm.id} className="space-y-0.5">
              {/* Community Node */}
              {(() => {
                const domains = comm.domains || [];
                return (
                  <>
                    <div
                      onClick={() => toggle(comm.id)}
                      className="flex items-center space-x-1.5 px-2 py-1.5 rounded hover:bg-accent/60 cursor-pointer text-xs font-medium text-foreground transition-colors group"
                    >
                      {domains.length > 0 ? (
                        isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        )
                      ) : (
                        <div className="w-3.5" />
                      )}
                      <Building2 className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-hover:text-primary transition-colors" />
                      <span className="truncate">{comm.name}</span>
                      <span className="ml-auto text-[10px] text-muted-foreground font-mono">
                        {domains.length}
                      </span>
                    </div>

                    {/* Child Domains */}
                    {isExpanded && (
                      <div className="pl-5 space-y-0.5 border-l border-border/40 ml-3">
                        {domains.map((dom) => {
                          const isSelected = selectedDomainId === dom.id;
                          return (
                            <div
                              key={dom.id}
                              onClick={() => onSelectDomain(dom)}
                              className={`flex items-center space-x-2 px-2 py-1.5 rounded text-xs cursor-pointer transition-colors ${
                                isSelected
                                  ? "bg-primary/10 text-primary font-medium border border-primary/20"
                                  : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              {getDomainIcon(dom.domain_type)}
                              <span className="truncate">{dom.name}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="h-8 px-3 border-t border-border flex items-center justify-between text-[10px] text-muted-foreground bg-muted/20">
        <span>Active Hierarchy</span>
        <span className="font-mono text-primary">Curated Operating Model</span>
      </div>
    </aside>
  );
};
