import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { DatabaseIcon, ServerIcon } from "lucide-react"

import type { ApplicationDetail, EnvironmentDetail } from "@/api"
import { getApplicationOptions } from "@/api/@tanstack/react-query.gen"
import {
  Button,
  DetailLayout,
  EmptyState,
  EntityHeader,
  ErrorState,
  LoadingState,
  NoAccessState,
  NotFoundState,
  STAGES,
  StageTracker,
  StatusBadge,
  stageTabId,
  useDetail,
  type Stage,
  type StageState,
} from "@/components/patterns"
import { useSearchParam } from "@/hooks/use-search-param"
import { ApplicationForm } from "@/features/applications/application-form"
import { DataStoreForm, EnvironmentForm } from "@/features/applications/know-forms"
import { CRITICALITY, DATA_STORE_TYPE, ENVIRONMENT_TYPE, HARVEST, HOSTING, LIFECYCLE } from "@/features/applications/labels"
import { problemStatus } from "@/features/applications/problem"
import { HarvestSection } from "@/features/harvest/harvest-section"

const PANEL_ID = "application-stage-panel"

function isStage(value: string | null): value is Stage {
  return STAGES.some((s) => s.id === value)
}

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
}

function stageStates(application: ApplicationDetail): Record<Stage, StageState> {
  const environments = application.environments.length
  const stores = application.environments.reduce((n, e) => n + e.data_stores.length, 0)
  // Short: the tracker truncates summaries in a narrow detail panel.
  const know: StageState =
    environments === 0
      ? { summary: "No environments", tone: "progress" }
      : stores === 0
        ? { summary: "No data stores", tone: "progress" }
        : { summary: plural(stores, "data store", "data stores"), tone: "complete" }
  const notStarted: StageState = { summary: "Not started", tone: "progress" }
  return { know, assess: notStarted, act: notStarted, assure: notStarted }
}

/** One application in the detail panel: header, stage tracker, the selected stage. */
export function ApplicationDetailView({ id }: { id: string }) {
  const query = useQuery(getApplicationOptions({ path: { application_id: id } }))
  const [editing, setEditing] = React.useState(false)

  if (query.isPending) return <LoadingState label="Loading application" />
  if (query.isError) {
    const status = problemStatus(query.error)
    if (status === 404 || status === 422) return <NotFoundState kind="application" />
    if (status === 403) return <NoAccessState requirement="access to this application’s domain" />
    return <ErrorState onRetry={() => void query.refetch()} retrying={query.isFetching} />
  }

  const application = query.data.data
  const actions = query.data.allowed_actions

  if (editing) {
    return (
      <DetailLayout header={<EntityHeader kind="Edit application" identifier={application.code} title={application.name} />}>
        <ApplicationForm application={application} onSaved={() => setEditing(false)} onCancel={() => setEditing(false)} />
      </DetailLayout>
    )
  }

  return (
    <DetailLayout
      header={
        <EntityHeader
          kind="Application"
          identifier={application.code}
          title={application.name}
          meta={[
            { label: "Domain", value: application.domain.name },
            { label: "Lifecycle", value: LIFECYCLE[application.lifecycle_status] },
            { label: "Criticality", value: CRITICALITY[application.criticality] },
            { label: "Hosting", value: HOSTING[application.hosting] },
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
      <ApplicationStages application={application} actions={actions} />
    </DetailLayout>
  )
}

function ApplicationStages({ application, actions }: { application: ApplicationDetail; actions: string[] }) {
  const [stageParam, setStage] = useSearchParam("stage")
  const stage: Stage = isStage(stageParam) ? stageParam : "know"

  return (
    <div className="flex flex-col gap-5">
      {application.description && <p className="text-sm text-muted-foreground">{application.description}</p>}
      <StageTracker
        entityName={application.name}
        states={stageStates(application)}
        selected={stage}
        onSelect={setStage}
        panelId={PANEL_ID}
      />
      <div role="tabpanel" id={PANEL_ID} aria-labelledby={stageTabId(PANEL_ID, stage)}>
        {stage === "know" && <KnowPanel application={application} actions={actions} />}
        {stage === "assess" && (
          <EmptyState
            title="No applied controls yet"
            description="Applied controls appear here once policies select this application’s data assets."
          />
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

function KnowPanel({ application, actions }: { application: ApplicationDetail; actions: string[] }) {
  const [adding, setAdding] = React.useState(false)
  const canAddEnvironment = actions.includes("add_environment")
  const canAddStore = actions.includes("add_data_store")

  return (
    <section aria-labelledby="environments-heading" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <h3 id="environments-heading" className="text-base font-semibold">
          Environments
        </h3>
        {canAddEnvironment && !adding && application.environments.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
            Add environment
          </Button>
        )}
      </div>

      {adding && <EnvironmentForm applicationId={application.id} onDone={() => setAdding(false)} />}

      {application.environments.length === 0 && !adding && (
        <EmptyState
          icon={ServerIcon}
          title="No environments yet"
          description="Add the production and non-production environments this application runs in."
          action={canAddEnvironment && <Button onClick={() => setAdding(true)}>Add environment</Button>}
        />
      )}

      {application.environments.map((environment) => (
        <EnvironmentSection key={environment.id} environment={environment} canAddStore={canAddStore} />
      ))}
    </section>
  )
}

function EnvironmentSection({ environment, canAddStore }: { environment: EnvironmentDetail; canAddStore: boolean }) {
  const [adding, setAdding] = React.useState(false)
  const headingId = `environment-${environment.id}`

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3 rounded-md border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <h4 id={headingId} className="text-sm font-semibold">
            {environment.name}
          </h4>
          <p className="text-xs text-muted-foreground">
            {ENVIRONMENT_TYPE[environment.type]} · {environment.region.name}
          </p>
        </div>
        {canAddStore && !adding && (
          <Button variant="ghost" size="sm" onClick={() => setAdding(true)}>
            Add data store
          </Button>
        )}
      </div>

      {environment.data_stores.length === 0 && !adding && (
        <p className="flex items-center gap-2 text-sm text-text-tertiary">
          <DatabaseIcon aria-hidden="true" className="size-4" />
          No data stores in this environment yet.
        </p>
      )}

      {environment.data_stores.length > 0 && (
        <ul aria-label={`Data stores in ${environment.name}`} className="flex flex-col divide-y">
          {environment.data_stores.map((store) => {
            const harvest = HARVEST[store.harvest_status]
            return (
              <li key={store.id} className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{store.name}</span>
                  <StatusBadge status={harvest.status} label={harvest.label} size="sm" />
                </div>
                <p className="text-xs text-muted-foreground">
                  {DATA_STORE_TYPE[store.type]} · {store.platform} · {store.region.name}
                </p>
                <p className="mono text-xs text-muted-foreground">{store.connection_ref}</p>
                <HarvestSection dataStoreId={store.id} storeName={store.name} />
              </li>
            )
          })}
        </ul>
      )}

      {adding && <DataStoreForm environmentId={environment.id} onDone={() => setAdding(false)} />}
    </section>
  )
}

/** The create form in the detail panel, at ?application=new. */
export function NewApplicationView() {
  const { open, close } = useDetail()
  return (
    <DetailLayout header={<EntityHeader kind="Application" title="Register an application" />}>
      <ApplicationForm onSaved={(application) => open(application.id)} onCancel={close} />
    </DetailLayout>
  )
}
