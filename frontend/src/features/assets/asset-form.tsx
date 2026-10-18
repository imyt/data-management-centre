import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Controller, useForm, useWatch, type Control, type Path } from "react-hook-form"
import { z } from "zod"

import type { AssetDetail } from "@/api"
import {
  createAssetMutation,
  listDataCategoriesOptions,
  listDomainsOptions,
  listRetentionPoliciesOptions,
  updateAssetMutation,
} from "@/api/@tanstack/react-query.gen"
import { Button, Field, fieldA11y, SelectInput, TextArea, TextInput, useDetail, type SelectOption } from "@/components/patterns"
import { optionsOf } from "@/features/applications/labels"
import { problemFieldErrors, problemMessage } from "@/features/applications/problem"
import { ASSET_TYPE, YES_NO } from "@/features/assets/labels"
import { invalidateAssets } from "@/features/assets/queries"

const NONE = "none"

const schema = z
  .object({
    name: z.string().trim().min(1, "Enter a name.").max(200, "Use 200 characters or fewer."),
    type: z.enum(["dataset", "report", "model", "file"]),
    description: z.string().trim().max(2000, "Use 2,000 characters or fewer."),
    domain_id: z.string().min(1, "Choose a domain."),
    data_category_id: z.string(),
    business_context: z.string().trim().max(2000, "Use 2,000 characters or fewer."),
    is_stored: z.enum(["yes", "no"]),
    retention_policy_id: z.string(),
  })
  .refine((v) => v.is_stored === "no" || (v.retention_policy_id !== "" && v.retention_policy_id !== NONE), {
    path: ["retention_policy_id"],
    message: "Choose a retention policy for a stored asset.",
  })

type Values = z.infer<typeof schema>

interface AssetFormProps {
  /** Edit this asset; declare a new one when absent. */
  asset?: AssetDetail
  onSaved: (asset: AssetDetail) => void
  onCancel: () => void
}

/** Declare or edit an asset: category, business context, stored flag and retention (FR-K5). */
export function AssetForm({ asset, onSaved, onCancel }: AssetFormProps) {
  const queryClient = useQueryClient()
  const { setDirty } = useDetail()
  const domains = useQuery(listDomainsOptions())
  const categories = useQuery(listDataCategoriesOptions())
  const policies = useQuery(listRetentionPoliciesOptions())
  const editing = asset !== undefined

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: {
      name: asset?.name ?? "",
      type: asset?.type ?? "dataset",
      description: asset?.description ?? "",
      domain_id: asset?.domain.id ?? "",
      data_category_id: asset?.data_category?.id ?? NONE,
      business_context: asset?.business_context ?? "",
      is_stored: asset?.is_stored ? "yes" : "no",
      retention_policy_id: asset?.retention_policy?.id ?? NONE,
    },
  })
  const { errors, isDirty } = form.formState
  const stored = useWatch({ control: form.control, name: "is_stored" }) === "yes"

  React.useEffect(() => setDirty(isDirty), [isDirty, setDirty])
  React.useEffect(() => () => setDirty(false), [setDirty])

  const create = useMutation(createAssetMutation())
  const update = useMutation(updateAssetMutation())
  const mutation = editing ? update : create
  const [formError, setFormError] = React.useState<string | null>(null)

  async function onSubmit(values: Values) {
    setFormError(null)
    const isStored = values.is_stored === "yes"
    const body = {
      name: values.name,
      type: values.type,
      description: values.description || null,
      domain_id: values.domain_id,
      data_category_id: values.data_category_id === NONE ? null : values.data_category_id,
      business_context: values.business_context || null,
      is_stored: isStored,
      retention_policy_id: isStored ? values.retention_policy_id : null,
    }
    try {
      const saved = editing
        ? await update.mutateAsync({ path: { asset_id: asset.id }, body })
        : await create.mutateAsync({ body })
      await invalidateAssets(queryClient)
      setDirty(false)
      onSaved(saved.data)
    } catch (error) {
      const fields = problemFieldErrors(error)
      const known = Object.entries(fields).filter(([field]) => field in values)
      for (const [field, message] of known) form.setError(field as Path<Values>, { message })
      if (known.length === 0) setFormError(problemMessage(error))
    }
  }

  const named = (items?: { id: string; name: string }[]): SelectOption[] => (items ?? []).map((i) => ({ value: i.id, label: i.name }))

  return (
    <form
      aria-label={editing ? `Edit ${asset.name}` : "Declare an asset"}
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <Field label="Name" htmlFor="asset-name" required error={errors.name?.message}>
        <TextInput {...form.register("name")} {...fieldA11y("asset-name", { error: errors.name?.message })} />
      </Field>
      <SelectField control={form.control} name="type" label="Type" options={optionsOf(ASSET_TYPE)} error={errors.type?.message} />
      <SelectField
        control={form.control}
        name="domain_id"
        label="Domain"
        options={named(domains.data?.data)}
        placeholder="Choose a domain"
        error={errors.domain_id?.message}
      />
      <SelectField
        control={form.control}
        name="data_category_id"
        label="Data category"
        required={false}
        options={[{ value: NONE, label: "Not declared yet" }, ...named(categories.data?.data)]}
        error={errors.data_category_id?.message}
      />
      <Field label="Business context" htmlFor="asset-business_context" hint="What the business uses it for." error={errors.business_context?.message}>
        <TextArea
          {...form.register("business_context")}
          {...fieldA11y("asset-business_context", { hint: "What the business uses it for.", error: errors.business_context?.message })}
        />
      </Field>
      <Field label="Description" htmlFor="asset-description" error={errors.description?.message}>
        <TextArea {...form.register("description")} {...fieldA11y("asset-description", { error: errors.description?.message })} />
      </Field>
      <SelectField control={form.control} name="is_stored" label="Stored" options={YES_NO} error={errors.is_stored?.message} />
      {stored && (
        <SelectField
          control={form.control}
          name="retention_policy_id"
          label="Retention policy"
          options={named(policies.data?.data)}
          placeholder="Choose a retention policy"
          error={errors.retention_policy_id?.message}
        />
      )}

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
          {editing ? "Save changes" : "Declare asset"}
        </Button>
      </div>
    </form>
  )
}

function SelectField(props: {
  control: Control<Values>
  name: "type" | "domain_id" | "data_category_id" | "is_stored" | "retention_policy_id"
  label: string
  options: SelectOption[]
  placeholder?: string
  required?: boolean
  error?: string
}) {
  const { control, name, label, options, placeholder, required = true, error } = props
  const id = `asset-${name}`
  return (
    <Field label={label} htmlFor={id} required={required} error={error}>
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
