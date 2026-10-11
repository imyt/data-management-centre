import { create } from "zustand";
import type { ThemeProps } from "@radix-ui/themes";

export type RadixAccentColor = NonNullable<ThemeProps["accentColor"]>;
export type RadixGrayColor = NonNullable<ThemeProps["grayColor"]>;
export type RadixRadius = NonNullable<ThemeProps["radius"]>;
export type RadixScaling = NonNullable<ThemeProps["scaling"]>;
export type RadixPanelBackground = NonNullable<ThemeProps["panelBackground"]>;

export interface IThemeStore {
  accentColor: RadixAccentColor;
  grayColor: RadixGrayColor;
  radius: RadixRadius;
  scaling: RadixScaling;
  panelBackground: RadixPanelBackground;
  isThemePanelOpen: boolean;
  setAccentColor: (color: RadixAccentColor) => void;
  setGrayColor: (gray: RadixGrayColor) => void;
  setRadius: (radius: RadixRadius) => void;
  setScaling: (scaling: RadixScaling) => void;
  setPanelBackground: (panelBg: RadixPanelBackground) => void;
  toggleThemePanel: () => void;
  setThemePanelOpen: (open: boolean) => void;
  resetTheme: () => void;
}

const STORAGE_KEY = "dg-centre-radix-theme";

const DEFAULT_THEME = {
  accentColor: "indigo" as RadixAccentColor,
  grayColor: "slate" as RadixGrayColor,
  radius: "medium" as RadixRadius,
  scaling: "100%" as RadixScaling,
  panelBackground: "translucent" as RadixPanelBackground,
  isThemePanelOpen: false,
};

function getInitialState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        ...DEFAULT_THEME,
        ...parsed,
        isThemePanelOpen: false,
      };
    }
  } catch {
    // Ignore storage read errors
  }
  return DEFAULT_THEME;
}

export const useThemeStore = create<IThemeStore>()((set, get) => ({
  ...getInitialState(),

  setAccentColor: (accentColor) => {
    set({ accentColor });
    saveSettings(get());
  },

  setGrayColor: (grayColor) => {
    set({ grayColor });
    saveSettings(get());
  },

  setRadius: (radius) => {
    set({ radius });
    saveSettings(get());
  },

  setScaling: (scaling) => {
    set({ scaling });
    saveSettings(get());
  },

  setPanelBackground: (panelBackground) => {
    set({ panelBackground });
    saveSettings(get());
  },

  toggleThemePanel: () => {
    // Dispatch keyboard event 't' to trigger the Radix ThemePanel toggle
    const event = new KeyboardEvent("keydown", {
      key: "t",
      code: "KeyT",
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);
    set((s) => ({ isThemePanelOpen: !s.isThemePanelOpen }));
  },

  setThemePanelOpen: (isThemePanelOpen) => set({ isThemePanelOpen }),

  resetTheme: () => {
    set({ ...DEFAULT_THEME });
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  },
}));

function saveSettings(state: IThemeStore) {
  try {
    const toSave = {
      accentColor: state.accentColor,
      grayColor: state.grayColor,
      radius: state.radius,
      scaling: state.scaling,
      panelBackground: state.panelBackground,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch {
    // Ignore storage write errors
  }
}
