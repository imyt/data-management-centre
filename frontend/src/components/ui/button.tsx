import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Loader2Icon } from "lucide-react"
import { Slot } from "radix-ui"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-sm text-sm font-medium whitespace-nowrap transition-colors duration-fast disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-brand-hover",
        destructive:
          "text-destructive hover:bg-danger-bg",
        outline:
          "border border-input bg-surface hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-border",
        ghost:
          "hover:bg-accent hover:text-accent-foreground",
        link: "text-brand underline-offset-4 hover:underline",
      },
      size: {
        default: "h-(--control-height) px-4 py-2 has-[>svg]:px-3",
        xs: "h-6 gap-1 rounded-sm px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 rounded-sm px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-sm px-6 has-[>svg]:px-4",
        icon: "size-(--control-height)",
        "icon-xs": "size-6 rounded-sm [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  loading = false,
  disabledReason,
  disabled,
  children,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
    /** Shows a spinner, sets aria-busy and blocks clicks. Keep the label. */
    loading?: boolean
    /** DESIGN.md: never disable without saying why. Shown in a tooltip and to screen readers. */
    disabledReason?: string
  }) {
  const Comp = asChild ? Slot.Root : "button"

  const button = (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {/* Slot needs exactly one child, so asChild passes it through untouched. */}
      {asChild ? (
        children
      ) : (
        <>
          {loading && <Loader2Icon className="animate-spin" aria-hidden="true" />}
          {children}
        </>
      )}
    </Comp>
  )

  if (!disabled || !disabledReason) return button

  // A disabled button gets no pointer or focus events, so the tooltip hangs off a focusable wrapper.
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} className="inline-flex rounded-sm">
          {button}
          <span className="sr-only">{disabledReason}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>{disabledReason}</TooltipContent>
    </Tooltip>
  )
}

export { Button, buttonVariants }
