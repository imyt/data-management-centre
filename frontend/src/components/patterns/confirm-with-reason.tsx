import * as React from "react"
import { CircleXIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

interface ConfirmWithReasonProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: React.ReactNode
  /** Impact preview, e.g. "Changes 12 assets, 3 of them Confidential." */
  impact?: React.ReactNode
  /** The action's own verb: "Accept risk", "Reject request". */
  confirmLabel: string
  destructive?: boolean
  requireReason?: boolean
  minReasonLength?: number
  /** Throw to keep the dialog open and show the error. */
  onConfirm: (reason: string) => Promise<void> | void
}

/** Risk decisions carry a reason, so the audit trail writes itself (DESIGN.md: Safe, accountable actions). */
export function ConfirmWithReason({ open, onOpenChange, title, description, ...form }: ConfirmWithReasonProps) {
  const [pending, setPending] = React.useState(false)
  return (
    <Dialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        {/* Unmounts with the content on close, so the reason and error start empty next time. */}
        <ReasonForm {...form} pending={pending} setPending={setPending} onDone={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

interface ReasonFormProps
  extends Pick<ConfirmWithReasonProps, "impact" | "confirmLabel" | "destructive" | "requireReason" | "minReasonLength" | "onConfirm"> {
  pending: boolean
  setPending: (pending: boolean) => void
  onDone: () => void
}

function ReasonForm({
  impact,
  confirmLabel,
  destructive = false,
  requireReason = true,
  minReasonLength = 10,
  onConfirm,
  pending,
  setPending,
  onDone,
}: ReasonFormProps) {
  const fieldId = React.useId()
  const [reason, setReason] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)

  const trimmed = reason.trim()
  const remaining = Math.max(0, minReasonLength - trimmed.length)
  const valid = !requireReason || remaining === 0

  async function handleConfirm() {
    if (!valid || pending) return
    setPending(true)
    setError(null)
    try {
      await onConfirm(trimmed)
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : "The action didn’t complete. Try again.")
    } finally {
      setPending(false)
    }
  }

  return (
    <>
      {impact && <div className="rounded-md bg-subtle px-3 py-2 text-sm">{impact}</div>}

      <div className="flex flex-col gap-1">
        <Label htmlFor={fieldId}>
          Reason
          {!requireReason && <span className="font-normal text-text-tertiary">(optional)</span>}
        </Label>
        <Textarea
          id={fieldId}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          aria-describedby={`${fieldId}-hint`}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleConfirm()
          }}
        />
        <p id={`${fieldId}-hint`} className="text-xs text-text-tertiary">
          {requireReason && remaining > 0
            ? `${remaining} more character${remaining === 1 ? "" : "s"} needed. Recorded in the audit trail.`
            : "Recorded in the audit trail."}
        </p>
      </div>

      {error && (
        <p role="alert" className="flex items-center gap-1 text-sm text-danger">
          <CircleXIcon className="size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      <DialogFooter>
        <Button variant="outline" onClick={onDone} disabled={pending}>
          Cancel
        </Button>
        <Button
          variant={destructive ? "destructive" : "default"}
          onClick={() => void handleConfirm()}
          loading={pending}
          disabled={!valid}
          disabledReason={requireReason ? `Enter a reason of at least ${minReasonLength} characters.` : undefined}
        >
          {confirmLabel}
        </Button>
      </DialogFooter>
    </>
  )
}
