import { useEffect } from "react";
import { Outlet, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components";
import { CommandPalette, useSearchUiStore } from "@/features/search";
import { CreateAssetModal, useCatalogUiStore } from "@/features/catalog";
import { PersonaProvider } from "@/context/PersonaContext";
import {
  listCommunitiesApiV1CommunitiesGetOptions,
  listAssetTypesApiV1MetamodelAssetTypesGetOptions,
  listAssetsApiV1AssetsGetOptions,
} from "@/api/client";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Theme, ThemePanel, useThemeContext } from "@radix-ui/themes";
import { usePersona } from "@/context/PersonaContext";
import { useThemeStore } from "@/stores/theme.store";

function RootContent() {
  const isCommandPaletteOpen = useSearchUiStore((s) => s.isOpen);
  const setCommandPaletteOpen = useSearchUiStore((s) => s.setOpen);
  const toggleCommandPalette = useSearchUiStore((s) => s.toggleOpen);

  const isCreateModalOpen = useCatalogUiStore((s) => s.isCreateModalOpen);
  const setCreateModalOpen = useCatalogUiStore((s) => s.setCreateModalOpen);

  const navigate = useNavigate();

  const { data: communities = [] } = useQuery(listCommunitiesApiV1CommunitiesGetOptions());
  const { data: assetTypes = [] } = useQuery(listAssetTypesApiV1MetamodelAssetTypesGetOptions());
  const { data: assets = [] } = useQuery(listAssetsApiV1AssetsGetOptions());

  const allDomains = communities.flatMap((c) => c.domains || []);

  // Global Cmd+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        toggleCommandPalette();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleCommandPalette]);

  return (
    <TooltipProvider>
      <div className="flex flex-col flex-1 h-full w-full overflow-hidden bg-background text-foreground font-sans">
        {/* Top Enterprise Header */}
        <Header />

        {/* Dynamic Route View */}
        <main className="flex-1 overflow-hidden relative flex">
          <Outlet />
        </main>

        {/* Global Cmd+K Command Palette */}
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
          assets={assets}
          communities={communities}
          onSelectAsset={(asset) => {
            navigate({
              to: "/catalog",
              search: (prev) => ({ ...prev, assetId: asset.id, domainId: asset.domain_id }),
            });
          }}
          onSelectDomain={(domain) => {
            navigate({
              to: "/catalog",
              search: (prev) => ({ ...prev, domainId: domain.id, assetId: undefined }),
            });
          }}
          onOpenCreateModal={() => setCreateModalOpen(true)}
        />

        {/* Propose Asset Modal */}
        <CreateAssetModal
          isOpen={isCreateModalOpen}
          onClose={() => setCreateModalOpen(false)}
          domains={allDomains}
          assetTypes={assetTypes}
        />
      </div>
    </TooltipProvider>
  );
}

function RadixThemeSynchronizer() {
  const themeContext = useThemeContext();
  const { setAccentColor, setGrayColor, setRadius, setScaling, setPanelBackground } = useThemeStore();

  useEffect(() => {
    if (themeContext.accentColor) {
      setAccentColor(themeContext.accentColor);
    }
  }, [themeContext.accentColor, setAccentColor]);

  useEffect(() => {
    if (themeContext.grayColor) {
      setGrayColor(themeContext.grayColor);
    }
  }, [themeContext.grayColor, setGrayColor]);

  useEffect(() => {
    if (themeContext.radius) {
      setRadius(themeContext.radius);
    }
  }, [themeContext.radius, setRadius]);

  useEffect(() => {
    if (themeContext.scaling) {
      setScaling(themeContext.scaling);
    }
  }, [themeContext.scaling, setScaling]);

  useEffect(() => {
    if (themeContext.panelBackground) {
      setPanelBackground(themeContext.panelBackground);
    }
  }, [themeContext.panelBackground, setPanelBackground]);

  return null;
}

function ThemedApp() {
  const { isDark } = usePersona();
  const { accentColor, grayColor, radius, scaling, panelBackground } = useThemeStore();

  return (
    <Theme
      appearance={isDark ? "dark" : "light"}
      accentColor={accentColor}
      grayColor={grayColor}
      radius={radius}
      scaling={scaling}
      panelBackground={panelBackground}
      hasBackground={true}
      className="h-screen w-screen overflow-hidden flex flex-col"
    >
      <RadixThemeSynchronizer />
      <RootContent />
      <ThemePanel defaultOpen={false} />
    </Theme>
  );
}

export function RootLayout() {
  return (
    <PersonaProvider>
      <ThemedApp />
    </PersonaProvider>
  );
}
