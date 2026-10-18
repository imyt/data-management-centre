import * as React from "react"

/** Page frame for a section screen: the title, then the content. */
export function Screen({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6 px-8 py-8">
      <h1 className="text-xl leading-tight font-semibold tracking-tight">{title}</h1>
      {children}
    </div>
  )
}
