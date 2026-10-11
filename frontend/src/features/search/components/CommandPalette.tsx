import React, { useEffect } from "react";
import { Command } from "cmdk";
import { Search, BookOpen, Folder, Hash } from "lucide-react";
import type { AssetHead, Community, Domain } from "@/api/client";

export interface ICommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  assets: AssetHead[];
  communities: Community[];
  onSelectAsset: (asset: AssetHead) => void;
  onSelectDomain: (domain: Domain) => void;
  onOpenCreateModal: () => void;
}

export const CommandPalette: React.FC<ICommandPaletteProps> = ({
  isOpen,
  onClose,
  assets,
  communities,
  onSelectAsset,
  onSelectDomain,
  onOpenCreateModal,
}) => {
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onClose();
      }
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [onClose]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/50 backdrop-blur-xs animate-in fade-in-0 duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl bg-card border border-border shadow-2xl rounded-lg overflow-hidden flex flex-col max-h-[70vh]"
      >
        <Command className="flex flex-col h-full w-full">
          <div className="flex items-center px-3 border-b border-border">
            <Search className="w-4 h-4 text-muted-foreground mr-2 shrink-0" />
            <Command.Input
              placeholder="Search assets, terms, domains, or actions... (Esc to close)"
              className="w-full h-11 bg-transparent border-0 outline-none text-foreground placeholder:text-muted-foreground text-xs"
              autoFocus
            />
          </div>

          <Command.List className="overflow-y-auto p-2 space-y-1">
            <Command.Empty className="py-6 text-center text-xs text-muted-foreground">
              No results found.
            </Command.Empty>

            <Command.Group heading="Quick Actions" className="text-[10px] uppercase font-semibold text-muted-foreground px-2 py-1">
              <Command.Item
                onSelect={() => {
                  onClose();
                  onOpenCreateModal();
                }}
                className="flex items-center space-x-2 px-2 py-1.5 rounded text-xs text-foreground hover:bg-accent cursor-pointer transition-colors"
              >
                <div className="w-4 h-4 rounded bg-primary/10 text-primary flex items-center justify-center">
                  <Hash className="w-3 h-3" />
                </div>
                <span>Propose New Governance Asset...</span>
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Governance Assets" className="text-[10px] uppercase font-semibold text-muted-foreground px-2 py-1">
              {assets.slice(0, 15).map((asset) => {
                const version = asset.published_version || asset.active_draft_version;
                return (
                  <Command.Item
                    key={asset.id}
                    onSelect={() => {
                      onClose();
                      onSelectAsset(asset);
                    }}
                    className="flex items-center space-x-2 px-2 py-1.5 rounded text-xs text-foreground hover:bg-accent cursor-pointer transition-colors"
                  >
                    <BookOpen className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span className="font-medium truncate">{version?.name || "Untitled Asset"}</span>
                    <span className="ml-auto text-[10px] text-muted-foreground font-mono">
                      v{version?.version_number}
                    </span>
                  </Command.Item>
                );
              })}
            </Command.Group>

            <Command.Group heading="Domains & Glossaries" className="text-[10px] uppercase font-semibold text-muted-foreground px-2 py-1">
              {communities.flatMap((c) => c.domains || []).map((dom) => (
                <Command.Item
                  key={dom.id}
                  onSelect={() => {
                    onClose();
                    onSelectDomain(dom);
                  }}
                  className="flex items-center space-x-2 px-2 py-1.5 rounded text-xs text-foreground hover:bg-accent cursor-pointer transition-colors"
                >
                  <Folder className="w-3.5 h-3.5 text-primary shrink-0" />
                  <span className="truncate">{dom.name}</span>
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
};
