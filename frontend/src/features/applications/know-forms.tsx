import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Controller, useForm, type Control, type FieldValues, type Path, type UseFormSetError } from "react-hook-form"
import { z } from "zod"

import {
  createDataStoreMutation,
  createEnvironmentMutation,
  listRegionsOptions,
} from "@/api/@tanstack/react-query.gen"
import { Button, Field, fieldA11y, SelectInput, TextInput, useDetail, type SelectOption } from "@/components/patterns"
import { DATA_STORE_TYPE, ENVIRONMENT_TYPE, optionsOf } from "@/features/applications/labels"
import { problemFieldErrors, problemMessage } from "@/features/applications/problem"
import { invalidateApplications } from "@/features/applications/queries"

/* ---------- shared ---------- */

function useRegionOptions(): SelectOption[] {
  const regions = useQuery(listRegionsOptions())
  return (regions.data?.data ?? []).map((r) => ({ value: r.id, label: r.name }))
}

function ControlledSelect<T extends FieldValues>(props: {
  control: Control<T>
  name: Path<T>
  id: string
  label: string
  options: SelectOption[]
  placeholder: string
  error?: string
}) {
  const { control, name, id, label, options, placeholder, error } = props
  return (
    <Field label={label} htmlFor={id} required error={error}>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <SelectInput
            {...fieldA11y(id, { error })}
            options={options}
            value={field.value}
            onValueChange={(value) => {
              field.onChange(value)
              field.onBlur()
            }}
            placeholder={placeholder}
          />
        )}
      />
    </Field>
  )
}

/** Puts server errors on their fields, or returns a form-level message when none match. */
function applyServerErrors<T extends FieldValues>(
  error: unknown,
  fields: string[],
  setError: UseFormSetError<T>
): string | null {
  const known = Object.entries(problemFieldErrors(error)).filter(([field]) => fields.includes(field))
  for (const [field, message] of known) setError(field as Path<T>, { message })
  return known.length ? null : problemMessage(error)
}

function FormActions({ pending, label, onCancel, error }: { pending: boolean; label: string; onCancel: () => void; error: string | null }) {
  return (
    <>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={pending}>
          {label}
        </Button>
      </div>
    </>
  )
}

/* ---------- environment ---------- */

const environmentSchema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use 200 characters or fewer."),
  type: z.enum(["production", "non_production"], { error: "Choose a type." }),
  region_id: z.string().min(1, "Choose a region."),
})
type EnvironmentValues = z.infer<typeof environmentSchema>

export function EnvironmentForm({ applicationId, onDone }: { applicationId: string; onDone: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const regions = useRegionOptions()
  const form = useForm<EnvironmentValues>({
    resolver: zodResolver(environmentSchema),
    mode: "onTouched",
    defaultValues: { name: "", region_id: "" },
  })
  const { errors, isDirty } = form.formState
  const mutation = useMutation(createEnvironmentMutation())
  const [formError, setFormError] = React.useState<string | null>(null)

  React.useEffect(() => setDirty(isDirty), [isDirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  async function onSubmit(values: EnvironmentValues) {
    setFormError(null)
    try {
      await mutation.mutateAsync({ path: { application_id: applicationId }, body: values })
      await invalidateApplications(queryClient)
      setDirty(false)
      onDone()
    } catch (error) {
      setFormError(applyServerErrors(error, Object.keys(values), form.setError))
    }
  }

  return (
    <form
      aria-label="Add an environment"
      className="flex flex-col gap-4 rounded-md border bg-surface p-4"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <Field label="Environment name" htmlFor="env-name" required error={errors.name?.message}>
        <TextInput {...form.register("name")} {...fieldA11y("env-name", { error: errors.name?.message })} />
      </Field>
      <ControlledSelect
        control={form.control}
        name="type"
        id="env-type"
        label="Type"
        options={optionsOf(ENVIRONMENT_TYPE)}
        placeholder="Choose a type"
        error={errors.type?.message}
      />
      <ControlledSelect
        control={form.control}
        name="region_id"
        id="env-region"
        label="Region"
        options={regions}
        placeholder="Choose a region"
        error={errors.region_id?.message}
      />
      <FormActions pending={mutation.isPending} label="Add environment" onCancel={onDone} error={formError} />
    </form>
  )
}

/* ---------- data store ---------- */

const CONNECTION_REF_HINT = "Where the secrets store keeps the credentials, e.g. vault:dmc/orders-db. Never a password."

const dataStoreSchema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use 200 characters or fewer."),
  type: z.enum(["relational", "document", "object_storage", "warehouse", "file_share"], { error: "Choose a type." }),
  platform: z.string().trim().min(1, "Enter the platform, e.g. PostgreSQL 18.").max(200, "Use 200 characters or fewer."),
  region_id: z.string().min(1, "Choose a region."),
  connection_ref: z
    .string()
    .trim()
    .regex(/^[a-z][a-z0-9+.-]*:[^\s@]+$/, "Enter a secret reference such as vault:dmc/orders-db, not a connection string."),
})
type DataStoreValues = z.infer<typeof dataStoreSchema>

export function DataStoreForm({ environmentId, onDone }: { environmentId: string; onDone: () => void }) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const regions = useRegionOptions()
  const form = useForm<DataStoreValues>({
    resolver: zodResolver(dataStoreSchema),
    mode: "onTouched",
    defaultValues: { name: "", platform: "", region_id: "", connection_ref: "" },
  })
  const { errors, isDirty } = form.formState
  const mutation = useMutation(createDataStoreMutation())
  const [formError, setFormError] = React.useState<string | null>(null)

  React.useEffect(() => setDirty(isDirty), [isDirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  async function onSubmit(values: DataStoreValues) {
    setFormError(null)
    try {
      await mutation.mutateAsync({ path: { environment_id: environmentId }, body: values })
      await invalidateApplications(queryClient)
      setDirty(false)
      onDone()
    } catch (error) {
      setFormError(applyServerErrors(error, Object.keys(values), form.setError))
    }
  }

  const id = (field: string) => `store-${environmentId}-${field}`

  return (
    <form
      aria-label="Add a data store"
      className="flex flex-col gap-4 rounded-md border bg-surface p-4"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <Field label="Data store name" htmlFor={id("name")} required error={errors.name?.message}>
        <TextInput {...form.register("name")} {...fieldA11y(id("name"), { error: errors.name?.message })} />
      </Field>
      <ControlledSelect
        control={form.control}
        name="type"
        id={id("type")}
        label="Type"
        options={optionsOf(DATA_STORE_TYPE)}
        placeholder="Choose a type"
        error={errors.type?.message}
      />
      <Field label="Platform" htmlFor={id("platform")} required error={errors.platform?.message}>
        <TextInput {...form.register("platform")} {...fieldA11y(id("platform"), { error: errors.platform?.message })} />
      </Field>
      <ControlledSelect
        control={form.control}
        name="region_id"
        id={id("region")}
        label="Region"
        options={regions}
        placeholder="Choose a region"
        error={errors.region_id?.message}
      />
      <Field
        label="Connection reference"
        htmlFor={id("connection_ref")}
        required
        hint={CONNECTION_REF_HINT}
        error={errors.connection_ref?.message}
      >
        <TextInput
          className="mono"
          autoComplete="off"
          {...form.register("connection_ref")}
          {...fieldA11y(id("connection_ref"), { hint: CONNECTION_REF_HINT, error: errors.connection_ref?.message })}
        />
      </Field>
      <FormActions pending={mutation.isPending} label="Add data store" onCancel={onDone} error={formError} />
    </form>
  )
}
