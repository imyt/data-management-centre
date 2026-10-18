import * as React from "react"
import { useQuery } from "@tanstack/react-query"

import type { AssetDetail } from "@/api"
import { getAssetOptions } from "@/api/@tanstack/react-query.gen"
import {
  Button,
  DetailLayout,
  EmptyState,
  EntityHeader,
  ErrorState,
  LoadingState,
  NoAccessState,
  NotFoundState,
  ReadOnlyField,
  STAGES,
  StageTracker,
  stageTabId,
  useDetail,
  type Stage,
  type StageState,
} from "@/components/patterns"
import { useSearchParam } from "@/hooks/use-search-param"
import { problemStatus } from "@/features/applications/problem"
import { AssetForm } from "@/features/assets/asset-form"
import { DataElementsSection } from "@/features/assets/data-elements-section"
import { ASSET_TYPE } from "@/features/assets/labels"
import { useAssessState } from "@/features/evaluation/use-assess-state"
import { AssessSection } from "@/features/evaluation/assess-section"
import { OwnershipSection } from "@/features/assets/ownership-section"

const PANEL_ID = "asset-stage-panel"

function isStage(value: string | null): value is Stage {
  return STAGES.some((s) => s.id === value)
}

function knowState(asset: AssetDetail): StageState {
  // Short: the tracker truncates summaries in a narrow detail panel.
  if (!asset.owner) return { summary: "No owner", tone: "progress" }
  if (asset.owner.status === "disputed") return { summary: "Owner disputed", tone: "progress" }
  if (asset.owner.status === "pending") return { summary: "Owner unconfirmed", tone: "progress" }
  if (!asset.data_category) return { summary: "No category", tone: "progress" }
  return { summary: "Owner confirmed", tone: "complete" }
}

/** One asset in the detail panel: header, stage tracker, the selected stage. */
export function AssetDetailView({ id }: { id: string }) {
  const query = useQuery(getAssetOptions({ path: { asset_id: id } }))
  const [editing, setEditing] = React.useState(false)

  if (query.isPending) return <LoadingState label="Loading asset" />
  if (query.isError) {
    const status = problemStatus(query.error)
    if (status === 404 || status === 422) return <NotFoundState kind="asset" />
    if (status === 403) return <NoAccessState requirement="access to this asset’s domain" />
    return <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
  }

  const asset = query.data.data
  const actions = query.data.allowed_actions

  if (editing) {
    return (
      <DetailLayout header={<EntityHeader kind="Edit asset" title={asset.name} />}>
        <AssetForm asset={asset} onSaved={() => setEditing(false)} onCancel={() => setEditing(false)} />
      </DetailLayout>
    )
  }

  return (
    <DetailLayout
      header={
        <EntityHeader
          kind={ASSET_TYPE[asset.type]}
          title={asset.name}
          meta={[
            { label: "Domain", value: asset.domain.name },
            { label: "Category", value: asset.data_category?.name ?? "Not declared" },
            { label: "Stored", value: asset.is_stored ? (asset.retention_policy?.name ?? "Yes") : "No" },
          ]}
          actions={
            actions.includes("edit") && (
              <Button variant="secondary" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )
          }
        />
      }
    >
      <AssetStages asset={asset} actions={actions} />
    </DetailLayout>
  )
}

function AssetStages({ asset, actions }: { asset: AssetDetail; actions: string[] }) {
  const [stageParam, setStage] = useSearchParam("stage")
  const stage: Stage = isStage(stageParam) ? stageParam : "know"
  const notStarted: StageState = { summary: "Not started", tone: "progress" }
  const assessState = useAssessState("asset", asset.id)

  return (
    <div className="flex flex-col gap-5">
      <StageTracker
        entityName={asset.name}
        states={{ know: knowState(asset), assess: assessState, act: notStarted, assure: notStarted }}
        selected={stage}
        onSelect={setStage}
        panelId={PANEL_ID}
      />
      <div role="tabpanel" id={PANEL_ID} aria-labelledby={stageTabId(PANEL_ID, stage)}>
        {stage === "know" && (
          <div className="flex flex-col gap-6">
            <Declaration asset={asset} />
            <OwnershipSection asset={asset} actions={actions} />
            <DataElementsSection asset={asset} actions={actions} />
          </div>
        )}
        {stage === "assess" && (
          <AssessSection subjectType="asset" subjectId={asset.id} />
        )}
        {stage === "act" && (
          <EmptyState title="No actions" description="Actions are raised here when an applied control fails." />
        )}
        {stage === "assure" && (
          <EmptyState title="No evaluation history" description="Results history appears here after the first evaluation." />
        )}
      </div>
    </div>
  )
}

function Declaration({ asset }: { asset: AssetDetail }) {
  return (
    <section aria-labelledby="declaration-heading" className="flex flex-col gap-3">
      <h3 id="declaration-heading" className="text-base font-semibold">
        Declaration
      </h3>
      <ReadOnlyField label="Business context" value={asset.business_context ?? "Not declared"} />
      {asset.description && <ReadOnlyField label="Description" value={asset.description} />}
      <ReadOnlyField label="Data category" value={asset.data_category?.name ?? "Not declared"} />
      <ReadOnlyField label="Retention" value={asset.is_stored ? (asset.retention_policy?.name ?? "—") : "Not stored"} />
    </section>
  )
}

/** The declare form in the detail panel, at ?asset=new. */
export function NewAssetView() {
  const { open, close } = useDetail()
  return (
    <DetailLayout header={<EntityHeader kind="Asset" title="Declare an asset" />}>
      <AssetForm onSaved={(asset) => open(asset.id)} onCancel={close} />
    </DetailLayout>
  )
}
