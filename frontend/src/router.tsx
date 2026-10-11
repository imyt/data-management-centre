import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { RootLayout } from "./routes/root";
import { CatalogPage } from "./routes/catalog";
import { InboxPage } from "./routes/inbox";
import { RemediationPage } from "./routes/remediation";
import { DataMovementPage } from "./routes/data-movement";
import { WorkbenchPage } from "./routes/workbench";
import { PoliciesPage } from "./routes/policies";

export interface CatalogSearch {
  domainId?: string;
  assetId?: string;
  search?: string;
  status?: string;
}

const rootRoute = createRootRoute({
  component: RootLayout,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/workbench" });
  },
});

const workbenchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workbench",
  component: WorkbenchPage,
});

const catalogRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/catalog",
  validateSearch: (search: Record<string, unknown>): CatalogSearch => {
    return {
      domainId: typeof search.domainId === "string" ? search.domainId : undefined,
      assetId: typeof search.assetId === "string" ? search.assetId : undefined,
      search: typeof search.search === "string" ? search.search : undefined,
      status: typeof search.status === "string" ? search.status : undefined,
    };
  },
  component: CatalogPage,
});

const inboxRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/inbox",
  component: InboxPage,
});

const remediationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/remediation",
  component: RemediationPage,
});

const dataMovementRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/data-movement",
  component: DataMovementPage,
});

const policiesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/policies",
  component: PoliciesPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  workbenchRoute,
  catalogRoute,
  inboxRoute,
  remediationRoute,
  dataMovementRoute,
  policiesRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
