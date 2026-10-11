import React, { useState } from "react";
import {
  Palette,
  Sun,
  Moon,
  Sparkles,
  Sliders,
  Check,
  RefreshCw,
} from "lucide-react";
import {
  Popover,
  Button as RadixButton,
  Badge as RadixBadge,
} from "@radix-ui/themes";
import {
  useThemeStore,
  type RadixAccentColor,
  type RadixRadius,
  type RadixScaling,
  type RadixGrayColor,
} from "@/stores/theme.store";
import { usePersona } from "@/context/PersonaContext";

const POPULAR_ACCENTS: { name: RadixAccentColor; color: string; label: string }[] = [
  { name: "indigo", color: "#3e63dd", label: "Indigo" },
  { name: "blue", color: "#0090ff", label: "Blue" },
  { name: "cyan", color: "#00a2c7", label: "Cyan" },
  { name: "teal", color: "#12a594", label: "Teal" },
  { name: "jade", color: "#29a383", label: "Jade" },
  { name: "green", color: "#30a46c", label: "Green" },
  { name: "grass", color: "#46a758", label: "Grass" },
  { name: "amber", color: "#ffc53d", label: "Amber" },
  { name: "orange", color: "#f76808", label: "Orange" },
  { name: "tomato", color: "#e54d2e", label: "Tomato" },
  { name: "red", color: "#e5484d", label: "Red" },
  { name: "ruby", color: "#e54666", label: "Ruby" },
  { name: "crimson", color: "#e93d82", label: "Crimson" },
  { name: "pink", color: "#d6409f", label: "Pink" },
  { name: "plum", color: "#ab4aba", label: "Plum" },
  { name: "purple", color: "#8e4ec6", label: "Purple" },
  { name: "violet", color: "#6e56cf", label: "Violet" },
  { name: "iris", color: "#5b5bd6", label: "Iris" },
  { name: "bronze", color: "#a18072", label: "Bronze" },
  { name: "gray", color: "#8d8d8d", label: "Gray" },
];

const RADII: { value: RadixRadius; label: string }[] = [
  { value: "none", label: "None" },
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
  { value: "full", label: "Full" },
];

const SCALINGS: RadixScaling[] = ["90%", "95%", "100%", "105%", "110%"];

const GRAYS: { value: RadixGrayColor; label: string }[] = [
  { value: "slate", label: "Slate" },
  { value: "gray", label: "Gray" },
  { value: "mauve", label: "Mauve" },
  { value: "sage", label: "Sage" },
  { value: "olive", label: "Olive" },
  { value: "sand", label: "Sand" },
];

export const ThemeCustomizer: React.FC = () => {
  const { isDark, toggleTheme } = usePersona();
  const {
    accentColor,
    setAccentColor,
    grayColor,
    setGrayColor,
    radius,
    setRadius,
    scaling,
    setScaling,
    resetTheme,
    toggleThemePanel,
  } = useThemeStore();

  const [isOpen, setIsOpen] = useState(false);

  return (
    <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
      <Popover.Trigger>
        <button
          className="px-2 py-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors flex items-center space-x-1.5 cursor-pointer border border-border/60 hover:border-border text-xs"
          title="Radix Theme Customizer (Press 'T' for full panel)"
        >
          <div
            className="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs"
            style={{ backgroundColor: "var(--accent-9)" }}
          />
          <Palette className="w-3.5 h-3.5 text-primary" />
          <span className="capitalize font-semibold text-[11px] text-foreground">
            {accentColor}
          </span>
        </button>
      </Popover.Trigger>

      <Popover.Content
        size="2"
        className="w-80 p-4 space-y-4 shadow-xl border border-border bg-card text-foreground"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="flex items-center space-x-1.5">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-bold text-xs">Radix Themes</span>
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={toggleTheme}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Toggle Light / Dark"
            >
              {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={resetTheme}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Reset to defaults"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 1. Accent Color Palette */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-foreground">Accent Color</span>
            <span className="text-muted-foreground capitalize font-mono text-[10px]">{accentColor}</span>
          </div>
          <div className="grid grid-cols-5 gap-1.5">
            {POPULAR_ACCENTS.map((item) => {
              const isSelected = accentColor === item.name;
              return (
                <button
                  key={item.name}
                  onClick={() => setAccentColor(item.name)}
                  className={`h-6 rounded flex items-center justify-center transition-all cursor-pointer relative ${
                    isSelected
                      ? "ring-2 ring-primary ring-offset-1 ring-offset-background scale-105"
                      : "hover:scale-105 opacity-90 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: item.color }}
                  title={item.label}
                >
                  {isSelected && <Check className="w-3.5 h-3.5 text-white drop-shadow-md" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Radius Selection */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-foreground">Corner Radius</span>
            <span className="text-muted-foreground capitalize font-mono text-[10px]">{radius}</span>
          </div>
          <div className="grid grid-cols-5 gap-1">
            {RADII.map((r) => {
              const isSelected = radius === r.value;
              return (
                <button
                  key={r.value}
                  onClick={() => setRadius(r.value)}
                  className={`py-1 text-[10px] font-medium transition-all cursor-pointer border ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary font-bold shadow-xs"
                      : "bg-muted/40 text-muted-foreground hover:text-foreground hover:bg-muted border-border/80"
                  } ${
                    r.value === "none"
                      ? "rounded-none"
                      : r.value === "small"
                      ? "rounded-xs"
                      : r.value === "medium"
                      ? "rounded-md"
                      : r.value === "large"
                      ? "rounded-lg"
                      : "rounded-full"
                  }`}
                >
                  {r.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Gray Color & Scaling */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          {/* Gray Color */}
          <div className="space-y-1">
            <span className="font-semibold text-foreground text-[11px]">Gray Palette</span>
            <select
              value={grayColor}
              onChange={(e) => setGrayColor(e.target.value as RadixGrayColor)}
              className="w-full text-xs p-1 rounded bg-muted/50 border border-border text-foreground font-medium outline-none cursor-pointer"
            >
              {GRAYS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>

          {/* Scaling */}
          <div className="space-y-1">
            <span className="font-semibold text-foreground text-[11px]">UI Scaling</span>
            <select
              value={scaling}
              onChange={(e) => setScaling(e.target.value as RadixScaling)}
              className="w-full text-xs p-1 rounded bg-muted/50 border border-border text-foreground font-medium outline-none cursor-pointer"
            >
              {SCALINGS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 4. Live Radix Component Preview */}
        <div className="space-y-1.5 pt-2 border-t border-border">
          <div className="text-[10px] text-muted-foreground font-medium">Live Radix UI Preview</div>
          <div className="flex items-center gap-2 flex-wrap">
            <RadixButton size="1" variant="solid">
              Solid Button
            </RadixButton>
            <RadixButton size="1" variant="soft">
              Soft Button
            </RadixButton>
            <RadixBadge size="1" color={accentColor} variant="solid">
              Badge
            </RadixBadge>
            <RadixBadge size="1" color={accentColor} variant="soft">
              Soft
            </RadixBadge>
          </div>
        </div>

        {/* 5. Radix Themes Native Panel Shortcut */}
        <div className="pt-2 border-t border-border flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground flex items-center gap-1">
            <Sliders className="w-3 h-3 text-primary" />
            <span>Developer Panel</span>
          </span>
          <button
            onClick={() => {
              setIsOpen(false);
              toggleThemePanel();
            }}
            className="text-[10px] px-2 py-0.5 rounded bg-muted hover:bg-muted/80 text-foreground font-semibold cursor-pointer border border-border"
          >
            Open Panel (T)
          </button>
        </div>
      </Popover.Content>
    </Popover.Root>
  );
};
