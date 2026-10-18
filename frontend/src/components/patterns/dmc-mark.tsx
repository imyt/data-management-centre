import { cn } from "@/lib/utils"

export type Stage = "know" | "assess" | "act" | "assure"

/** Clockwise from top left, matching the corners of the mark. */
export const STAGES: { id: Stage; label: string }[] = [
  { id: "know", label: "Know" },
  { id: "assess", label: "Assess" },
  { id: "act", label: "Act" },
  { id: "assure", label: "Assure" },
]

const CORNERS = ["M 8 34 V 8 H 34", "M 66 8 H 92 V 34", "M 92 66 V 92 H 66", "M 34 92 H 8 V 66"]
const DIAMOND = "M 50 33 L 67 50 L 50 67 L 33 50 Z"
/** At 16px and below a smaller diamond keeps the gap to the corners readable. */
const DIAMOND_SMALL = "M 50 37 L 63 50 L 50 63 L 37 50 Z"

interface DmcMarkProps {
  size?: number
  /** Lights only these stages' corners; omit for the full brand mark. */
  lit?: Stage[]
  /** Accessible name. Pass "" when a visible wordmark sits next to it. */
  title?: string
  className?: string
}

/** Four corners (Know, Assess, Act, Assure) governing the data asset at the centre (DESIGN.md: Mark). */
export function DmcMark({ size = 24, lit, title = "DMC", className }: DmcMarkProps) {
  const decorative = title === ""
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      data-slot="dmc-mark"
      className={cn("shrink-0", className)}
      {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": title })}
    >
      {CORNERS.map((d, i) => {
        const on = !lit || lit.includes(STAGES[i].id)
        return (
          <path
            key={d}
            d={d}
            fill="none"
            strokeWidth={12}
            strokeLinejoin="miter"
            className={cn("transition-colors duration-base", on ? "stroke-primary" : "stroke-mark-idle")}
          />
        )
      })}
      <path d={size <= 16 ? DIAMOND_SMALL : DIAMOND} className="fill-primary" />
    </svg>
  )
}
