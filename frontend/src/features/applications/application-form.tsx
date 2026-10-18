import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Controller, useForm, type Path } from "react-hook-form"
import { z } from "zod"

import type { ApplicationDetail } from "@/api"
import {
  createApplicationMutation,
  listDomainsOptions,
  updateApplicationMutation,
} from "@/api/@tanstack/react-query.gen"
import { Button, Field, fieldA11y, SelectInput, TextArea, TextInput, useDetail } from "@/components/patterns"
import { CRITICALITY, HOSTING, LIFECYCLE, optionsOf } from "@/features/applications/labels"
import { problemFieldErrors, problemMessage } from "@/features/applications/problem"
import { invalidateApplications } from "@/features/applications/queries"

const schema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use 200 characters or fewer."),
  code: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$/, "Use 2 to 40 letters, digits, hyphens or underscores."),
  description: z.string().trim().max(2000, "Use 2,000 characters or fewer."),
  domain_id: z.string().min(1, "Choose a domain."),
  criticality: z.enum(["low", "medium", "high", "critical"], { error: "Choose a criticality." }),
  hosting: z.enum(["on_premises", "private_cloud", "public_cloud", "saas"], { error: "Choose where it is hosted." }),
  lifecycle_status: z.enum(["planned", "active", "retiring", "decommissioned"]),
})

type Values = z.infer<typeof schema>

const NEW_LIFECYCLE = { planned: LIFECYCLE.planned, active: LIFECYCLE.active }

interface ApplicationFormProps {
  /** Edit this application; register a new one when absent. */
  application?: ApplicationDetail
  onSaved: (application: ApplicationDetail) => void
  onCancel: () => void
}

/** Register or edit an application (FR-K1). Server errors land on their fields. */
export function ApplicationForm({ application, onSaved, onCancel }: ApplicationFormProps) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const domains = useQuery(listDomainsOptions())
  const editing = application !== undefined

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: {
      name: application?.name ?? "",
      code: application?.code ?? "",
      description: application?.description ?? "",
      domain_id: application?.domain.id ?? "",
      criticality: application?.criticality,
      hosting: application?.hosting,
      lifecycle_status: application?.lifecycle_status ?? "planned",
    },
  })
  const { errors, isDirty } = form.formState

  React.useEffect(() => setDirty(isDirty), [isDirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  const create = useMutation(createApplicationMutation())
  const update = useMutation(updateApplicationMutation())
  const mutation = editing ? update : create
  const [formError, setFormError] = React.useState<string | null>(null)

  async function onSubmit(values: Values) {
    setFormError(null)
    const body = { ...values, description: values.description || null }
    try {
      const saved = editing
        ? await update.mutateAsync({ path: { application_id: application.id }, body })
        : await create.mutateAsync({ body })
      await invalidateApplications(queryClient)
      setDirty(false)
      onSaved(saved.data)
    } catch (error) {
      const fields = problemFieldErrors(error)
      const known = Object.entries(fields).filter(([field]) => field in values)
      for (const [field, message] of known) form.setError(field as Path<Values>, { message })
      if (known.length === 0) setFormError(problemMessage(error))
    }
  }

  const domainOptions = (domains.data?.data ?? []).map((d) => ({ value: d.id, label: d.name }))
  const lifecycleOptions = optionsOf(editing ? LIFECYCLE : NEW_LIFECYCLE)

  return (
    <form
      aria-label={editing ? `Edit ${application.name}` : "Register an application"}
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <Field label="Name" htmlFor="app-name" required error={errors.name?.message}>
        <TextInput {...form.register("name")} {...fieldA11y("app-name", { error: errors.name?.message })} />
      </Field>
      <Field
        label="Code"
        htmlFor="app-code"
        required
        hint="A short unique code, e.g. ORD."
        error={errors.code?.message}
      >
        <TextInput
          className="mono"
          {...form.register("code")}
          {...fieldA11y("app-code", { hint: "A short unique code, e.g. ORD.", error: errors.code?.message })}
        />
      </Field>
      <Field label="Description" htmlFor="app-description" error={errors.description?.message}>
        <TextArea
          {...form.register("description")}
          {...fieldA11y("app-description", { error: errors.description?.message })}
        />
      </Field>
      <SelectField form={form} name="domain_id" label="Domain" options={domainOptions} placeholder="Choose a domain" />
      <SelectField
        form={form}
        name="criticality"
        label="Criticality"
        options={optionsOf(CRITICALITY)}
        placeholder="Choose a criticality"
      />
      <SelectField form={form} name="hosting" label="Hosting" options={optionsOf(HOSTING)} placeholder="Choose hosting" />
      <SelectField form={form} name="lifecycle_status" label="Lifecycle" options={lifecycleOptions} />

      {formError && (
        <p role="alert" className="text-sm text-danger">
          {formError}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={mutation.isPending}>
          {editing ? "Save changes" : "Register application"}
        </Button>
      </div>
    </form>
  )
}

interface SelectFieldProps {
  form: ReturnType<typeof useForm<Values>>
  name: "domain_id" | "criticality" | "hosting" | "lifecycle_status"
  label: string
  options: { value: string; label: string }[]
  placeholder?: string
}

function SelectField({ form, name, label, options, placeholder }: SelectFieldProps) {
  const id = `app-${name.replace("_", "-")}`
  const error = form.formState.errors[name]?.message
  return (
    <Field label={label} htmlFor={id} required error={error}>
      <Controller
        control={form.control}
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
