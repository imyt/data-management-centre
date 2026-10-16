import * as React from "react"

export type Theme = "light" | "dark"
export type Density = "comfortable" | "compact"

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
  density: Density
  setDensity: (density: Density) => void
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null)

const THEME_KEY = "dmc-theme"
const DENSITY_KEY = "dmc-density"

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    return allowed.includes(value as T) ? (value as T) : fallback
  } catch {
    return fallback
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Storage can be unavailable (private mode); the choice then lasts for the session only.
  }
}

/** Applies `.dark` and `data-density` to <html>, as tokens.css expects, and persists both per user. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(() =>
    read(THEME_KEY, ["light", "dark"] as const, "light")
  )
  const [density, setDensityState] = React.useState<Density>(() =>
    read(DENSITY_KEY, ["comfortable", "compact"] as const, "comfortable")
  )

  React.useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
    document.documentElement.style.colorScheme = theme
  }, [theme])

  React.useLayoutEffect(() => {
    document.documentElement.dataset.density = density
  }, [density])

  const value = React.useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme: (next) => {
        write(THEME_KEY, next)
        setThemeState(next)
      },
      density,
      setDensity: (next) => {
        write(DENSITY_KEY, next)
        setDensityState(next)
      },
    }),
    [theme, density]
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside ThemeProvider")
  return context
}
