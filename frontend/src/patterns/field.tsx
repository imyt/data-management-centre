import * as React from "react"
import { CircleXIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Label } from "@/ui/label"

interface FieldProps {
  label: string
  /** id of the control; wires the label, hint and error to it. */
  htmlFor: string
  hint?: string
  /** Plain-language validation message. Sets the error state. */
  error?: string
  required?: boolean
  className?: string
  /** One control. Pass `aria-invalid` and `aria-describedby` from `fieldA11y()`. */
  children: React.ReactNode
}

export function fieldA11y(id: string, { hint, error }: { hint?: string; error?: string }) {
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ")
  return {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy || undefined,
  } as const
}

/** Label above, control, hint, inline error. DESIGN.md: never a placeholder as the only label. */
export function Field({ label, htmlFor, hint, error, required, className, children }: FieldProps) {
  return (
    <div data-slot="field" className={cn("flex max-w-(--content-max) flex-col gap-1", className)}>
      <Label htmlFor={htmlFor}>
        {label}
        {!required && <span className="font-normal text-text-tertiary">(optional)</span>}
      </Label>
      {children}
      {hint && (
        <p id={`${htmlFor}-hint`} className="text-xs text-text-tertiary">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${htmlFor}-error`} className="flex items-center gap-1 text-xs text-danger">
          <CircleXIcon className="size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  )
}

interface ReadOnlyFieldProps {
  label: string
  value?: React.ReactNode
  /** Who or what controls the field, when it isn't obvious. */
  controlledBy?: string
  className?: string
}

/** DESIGN.md: read-only fields look like plain text, not greyed-out inputs. Empty shows an em dash. */
export function ReadOnlyField({ label, value, controlledBy, className }: ReadOnlyFieldProps) {
  const empty = value === undefined || value === null || value === ""
  return (
    <div data-slot="read-only-field" className={cn("flex flex-col gap-1", className)}>
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <span className={cn("py-1 text-sm", empty ? "text-text-tertiary" : "text-foreground")}>
        {empty ? "—" : value}
      </span>
      {controlledBy && <span className="text-xs text-text-tertiary">{controlledBy}</span>}
    </div>
  )
}
