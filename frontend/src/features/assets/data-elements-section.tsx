import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { TableIcon } from "lucide-react"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import type { AssetDetail, DataElementRead } from "@/api"
import { createDataElementMutation, updateDataElementMutation } from "@/api/@tanstack/react-query.gen"
import { Button, EmptyState, Field, fieldA11y, SelectInput, TextInput } from "@/components/patterns"
import { problemFieldErrors, problemMessage } from "@/features/applications/problem"
import { YES_NO } from "@/features/assets/labels"
import { invalidateAssets } from "@/features/assets/queries"

/** The data elements of an asset, with the PII declaration and the Data Owner's CDE flag (FR-K6). */
export function DataElementsSection({ asset, actions }: { asset: AssetDetail; actions: string[] }) {
  const [adding, setAdding] = React.useState(false)
  const canEdit = actions.includes("edit_elements")
  const canFlagCde = actions.includes("flag_cde")

  return (
    <section aria-labelledby="elements-heading" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 id="elements-heading" className="text-base font-semibold">
          Data elements
        </h3>
        {canEdit && !adding && asset.data_elements.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
            Add data element
          </Button>
        )}
      </div>

      {adding && <ElementForm asset={asset} canFlagCde={canFlagCde} onDone={() => setAdding(false)} />}

      {asset.data_elements.length === 0 && !adding && (
        <EmptyState
          icon={TableIcon}
          title="No data elements yet"
          description="Add the fields or columns of this asset to flag personal data and critical data elements."
          action={canEdit && <Button onClick={() => setAdding(true)}>Add data element</Button>}
        />
      )}

      {asset.data_elements.length > 0 && (
        <ul aria-label={`Data elements of ${asset.name}`} className="flex flex-col divide-y rounded-md border px-4">
          {asset.data_elements.map((element) => (
            <ElementRow key={element.id} element={element} canEdit={canEdit} canFlagCde={canFlagCde} />
          ))}
        </ul>
      )}
    </section>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="mono rounded-sm bg-subtle px-1.5 py-0.5 text-xs font-medium">{children}</span>
}

function ElementRow({ element, canEdit, canFlagCde }: { element: DataElementRead; canEdit: boolean; canFlagCde: boolean }) {
  const queryClient = useQueryClient()
  const update = useMutation(updateDataElementMutation())
  const [error, setError] = React.useState<string | null>(null)

  async function toggle(body: { is_pii: boolean } | { is_cde: boolean }) {
    setError(null)
    try {
      await update.mutateAsync({ path: { element_id: element.id }, body })
      await invalidateAssets(queryClient)
    } catch (e) {
      setError(problemMessage(e))
    }
  }

  return (
    <li className="flex flex-col gap-1 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{element.name}</span>
          <span className="mono text-xs text-muted-foreground">{element.data_type}</span>
          {element.is_pii && <Tag>PII</Tag>}
          {element.is_cde && <Tag>CDE</Tag>}
        </div>
        <div className="flex gap-1">
          {canEdit && (
            <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => void toggle({ is_pii: !element.is_pii })}>
              {element.is_pii ? "Not personal data" : "Declare as PII"}
            </Button>
          )}
          {canFlagCde && (
            <Button variant="ghost" size="sm" disabled={update.isPending} onClick={() => void toggle({ is_cde: !element.is_cde })}>
              {element.is_cde ? "Remove CDE flag" : "Flag as CDE"}
            </Button>
          )}
        </div>
      </div>
      {element.is_pii && element.pii_source && (
        <p className="text-xs text-muted-foreground">PII {element.pii_source === "declared" ? "declared by a person" : "found by a scanner"}.</p>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </li>
  )
}

const schema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use 200 characters or fewer."),
  data_type: z.string().trim().min(1, "Enter the data type, e.g. text.").max(100, "Use 100 characters or fewer."),
  is_pii: z.enum(["yes", "no"]),
  is_cde: z.enum(["yes", "no"]),
})
type Values = z.infer<typeof schema>

function ElementForm({ asset, canFlagCde, onDone }: { asset: AssetDetail; canFlagCde: boolean; onDone: () => void }) {
  const queryClient = useQueryClient()
  const create = useMutation(createDataElementMutation())
  const [formError, setFormError] = React.useState<string | null>(null)
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: { name: "", data_type: "", is_pii: "no", is_cde: "no" },
  })
  const { errors } = form.formState

  async function onSubmit(values: Values) {
    setFormError(null)
    try {
      await create.mutateAsync({
        path: { asset_id: asset.id },
        body: { name: values.name, data_type: values.data_type, is_pii: values.is_pii === "yes", is_cde: values.is_cde === "yes" },
      })
      await invalidateAssets(queryClient)
      onDone()
    } catch (error) {
      const fields = problemFieldErrors(error)
      const known = Object.entries(fields).filter(([field]) => field in values)
      for (const [field, message] of known) form.setError(field as keyof Values, { message })
      if (known.length === 0) setFormError(problemMessage(error))
    }
  }

  return (
    <form
      aria-label="Add a data element"
      className="flex flex-col gap-4 rounded-md border bg-surface p-4"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <Field label="Name" htmlFor="element-name" required error={errors.name?.message}>
        <TextInput {...form.register("name")} {...fieldA11y("element-name", { error: errors.name?.message })} />
      </Field>
      <Field label="Data type" htmlFor="element-data_type" required error={errors.data_type?.message}>
        <TextInput
          className="mono"
          {...form.register("data_type")}
          {...fieldA11y("element-data_type", { error: errors.data_type?.message })}
        />
      </Field>
      <Field label="Personal data (PII)" htmlFor="element-is_pii" required>
        <Controller
          control={form.control}
          name="is_pii"
          render={({ field }) => (
            <SelectInput {...fieldA11y("element-is_pii", {})} options={YES_NO} value={field.value} onValueChange={field.onChange} />
          )}
        />
      </Field>
      {canFlagCde && (
        <Field label="Critical data element (CDE)" htmlFor="element-is_cde" required>
          <Controller
            control={form.control}
            name="is_cde"
            render={({ field }) => (
              <SelectInput {...fieldA11y("element-is_cde", {})} options={YES_NO} value={field.value} onValueChange={field.onChange} />
            )}
          />
        </Field>
      )}
      {formError && (
        <p role="alert" className="text-sm text-danger">
          {formError}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" loading={create.isPending}>
          Add data element
        </Button>
      </div>
    </form>
  )
}
