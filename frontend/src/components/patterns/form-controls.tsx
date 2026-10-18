import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

// Form controls for screens. Button, Input and Textarea are the primitives themselves; every state of
// each is in the gallery's ui section. Pair each control with <Field> and fieldA11y().
export { Button, Input as TextInput, Textarea as TextArea }

export interface SelectOption {
  value: string
  label: string
}

interface SelectInputProps {
  id: string
  options: SelectOption[]
  value: string | undefined
  onValueChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  /** Name for screen readers when no <Field> label points at `id`. */
  "aria-label"?: string
  "aria-invalid"?: boolean
  "aria-describedby"?: string
  className?: string
}

/** A select over a fixed list of options (the gallery's Select, with a simpler API). */
export function SelectInput({ id, options, value, onValueChange, placeholder, disabled, className, ...aria }: SelectInputProps) {
  return (
    <Select value={value ?? ""} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger id={id} className={cn("w-full", className)} {...aria}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      {/* z-modal!: forms also open in DetailSplit’s sheet, whose overlay sits above z-popover. Same layer, later in the DOM, so on top. */}
      <SelectContent className="z-modal!">
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
