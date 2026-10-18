import * as React from "react"

export const STATES = ["default", "hover", "focus", "disabled", "loading", "error", "empty"] as const
export type GalleryState = (typeof STATES)[number]

/** A state either renders, or says why it doesn't apply to this component. */
export type StateCell = React.ReactNode | { na: string }

export interface GalleryEntry {
  id: string
  name: string
  layer: "ui" | "patterns"
  /** One sentence: what it is and when to use it. */
  summary: string
  states: Record<GalleryState, StateCell>
  /** Table-like content needs wider state cells so it doesn't scroll inside them. */
  wide?: boolean
  /** Extra variants worth seeing next to the states (e.g. every button variant). */
  variants?: React.ReactNode
}

function isNotApplicable(cell: StateCell): cell is { na: string } {
  return typeof cell === "object" && cell !== null && "na" in cell && !React.isValidElement(cell)
}

const stateHint: Partial<Record<GalleryState, string>> = {
  hover: "Point at it",
  focus: "Tab to it",
}

export function Specimen({ entry }: { entry: GalleryEntry }) {
  const headingId = `${entry.id}-heading`
  return (
    <section id={entry.id} aria-labelledby={headingId} data-gallery-entry={entry.id} className="scroll-mt-16">
      <div className="mb-4 flex items-baseline gap-3">
        <h2 id={headingId} className="text-xl leading-tight font-semibold tracking-tight">
          {entry.name}
        </h2>
        <span className="mono text-text-tertiary">src/{entry.layer}</span>
      </div>
      <p className="mb-6 max-w-(--content-max) text-sm text-muted-foreground">{entry.summary}</p>

      {entry.variants && (
        <div className="mb-6 rounded-md bg-surface p-4" data-gallery-variants>
          <p className="mb-3 text-xs text-text-tertiary">Variants</p>
          {entry.variants}
        </div>
      )}

      <div className={entry.wide ? "grid grid-cols-1 gap-4 2xl:grid-cols-2" : "grid grid-cols-4 gap-4 2xl:grid-cols-7"}>
        {STATES.map((state) => {
          const cell = entry.states[state]
          const na = isNotApplicable(cell)
          return (
            <div
              key={state}
              data-gallery-state={state}
              className="flex min-h-32 flex-col gap-3 rounded-md bg-surface p-4"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-medium text-foreground">{state[0].toUpperCase() + state.slice(1)}</span>
                {!na && stateHint[state] && <span className="text-xs text-text-tertiary">{stateHint[state]}</span>}
              </div>
              {na ? (
                <p className="text-xs text-text-tertiary">Not applicable: {cell.na}</p>
              ) : (
                <div data-gallery-target className="flex flex-1 flex-wrap items-start gap-2">
                  {cell}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
