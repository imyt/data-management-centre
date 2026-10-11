import React from "react";
import { Link } from "@tanstack/react-router";
import { Search, Shield, Moon, Sun, UserCheck, Inbox, CheckSquare, Layers, ArrowRightLeft, LayoutDashboard, Sliders } from "lucide-react";
import { usePersona, type PersonaRole } from "../context/PersonaContext";
import { useSearchUiStore } from "@/features/search";
import { ThemeCustomizer } from "./ThemeCustomizer";
import { useQuery } from "@tanstack/react-query";
import { verificationApi } from "@/features/inbox/api/verificationApi";
import type { Domain } from "../api/client";

export interface IHeaderProps {
  activeDomain?: Domain | null;
}

export const Header: React.FC<IHeaderProps> = ({ activeDomain }) => {
  const {
    currentRole,
    setCurrentRole,
    isDark,
    toggleTheme,
  } = usePersona();
  const setCommandPaletteOpen = useSearchUiStore((s) => s.setOpen);

  const { data: verificationsData } = useQuery({
    queryKey: ["steward-verifications"],
    queryFn: () => verificationApi.listPendingVerifications(),
    staleTime: 30000,
  });
  const pendingVerificationsCount = verificationsData?.summary.total_pending ?? 0;

  return (
    <header className="h-11 border-b border-border bg-card flex items-center justify-between px-3 shrink-0 select-none">
      {/* Brand & Breadcrumbs & Navigation */}
      <div className="flex items-center space-x-3">
        <Link to="/workbench" className="flex items-center space-x-1.5 font-bold tracking-tight text-foreground hover:opacity-90 transition-opacity">
          <div className="w-5 h-5 rounded bg-primary flex items-center justify-center text-primary-foreground shadow-xs">
            <Shield className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs">Data Management Centre</span>
        </Link>

        {/* Global Route Navigation Links */}
        <nav className="flex items-center space-x-1 border-l border-border pl-3 ml-1">
          <Link
            to="/workbench"
            className="flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Workbench</span>
            <span className="px-1.5 py-0.2 text-[10px] bg-red-500/15 text-red-600 dark:text-red-400 font-mono font-bold rounded-full">
              4
            </span>
          </Link>

          <Link
            to="/catalog"
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Catalog</span>
          </Link>

          <Link
            to="/inbox"
            className="flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <Inbox className="w-3.5 h-3.5" />
            <span>Inbox</span>
            <span className="px-1.5 py-0.2 text-[10px] bg-amber-500/15 text-amber-600 dark:text-amber-400 font-mono font-bold rounded-full">
              {3 + pendingVerificationsCount}
            </span>
          </Link>

          <Link
            to="/remediation"
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <CheckSquare className="w-3.5 h-3.5" />
            <span>Remediation</span>
          </Link>

          <Link
            to="/data-movement"
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Data Movement</span>
          </Link>

          <Link
            to="/policies"
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50 [&.active]:bg-primary/10 [&.active]:text-primary [&.active]:font-semibold"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Policies</span>
          </Link>
        </nav>

        {activeDomain && (
          <div className="hidden lg:flex items-center text-xs text-muted-foreground border-l border-border pl-3">
            <span className="text-muted-foreground/50">Domain:</span>
            <span className="ml-1.5 font-medium text-foreground truncate max-w-[140px]">
              {activeDomain.name}
            </span>
          </div>
        )}
      </div>

      {/* Global Cmd+K Search Trigger */}
      <button
        onClick={() => setCommandPaletteOpen(true)}
        className="flex items-center space-x-2 px-2.5 py-1 rounded bg-muted/60 hover:bg-muted border border-border/80 text-muted-foreground hover:text-foreground text-xs transition-colors w-72 lg:w-80 justify-between"
      >
        <div className="flex items-center space-x-1.5">
          <Search className="w-3.5 h-3.5" />
          <span className="truncate">Search catalog, policies, systems...</span>
        </div>
        <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-card border border-border rounded text-muted-foreground shadow-xs">
          ⌘K
        </kbd>
      </button>

      {/* Persona Switcher & Theme Toggle */}
      <div className="flex items-center space-x-2">
        {/* Role Persona Selector */}
        <div className="flex items-center space-x-1.5 bg-muted/50 px-2 py-0.5 rounded border border-border/60">
          <UserCheck className="w-3.5 h-3.5 text-primary" />
          <span className="text-[10px] text-muted-foreground uppercase font-medium hidden sm:inline">Persona:</span>
          <select
            value={currentRole}
            onChange={(e) => setCurrentRole(e.target.value as PersonaRole)}
            className="bg-transparent border-0 text-xs text-foreground font-medium outline-none cursor-pointer py-0.5"
          >
            <option value="DATA_STEWARD">Sarah Chen (Data Steward)</option>
            <option value="BUSINESS_OWNER">David Vance (Domain Owner)</option>
            <option value="APP_OWNER">Elena Rostova (System Owner)</option>
            <option value="DATA_CONSUMER">Jordan Patel (Data Consumer)</option>
            <option value="PLATFORM_ADMIN">Alex Mercer (Platform Admin)</option>
          </select>
        </div>

        {/* Radix Themes Customizer Popover */}
        <ThemeCustomizer />

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={isDark ? "Switch to Light Mode (or press 'D')" : "Switch to Dark Mode (or press 'D')"}
          className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
