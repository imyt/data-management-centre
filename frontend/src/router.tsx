import { createBrowserRouter } from "react-router"

import { ApplicationsPage } from "@/features/applications/applications-page"
import { AssetsPage } from "@/features/assets/assets-page"
import { ControlsPage } from "@/features/controls/controls-page"
import { GalleryPage } from "@/features/gallery/gallery-page"
import { InboxPage } from "@/features/inbox/inbox-page"
import { NotFoundPage } from "@/features/not-found/not-found-page"
import { ReportsPage } from "@/features/reports/reports-page"
import { AppLayout } from "@/features/shell/app-layout"

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <InboxPage /> },
      { path: "assets", element: <AssetsPage /> },
      { path: "applications", element: <ApplicationsPage /> },
      { path: "controls", element: <ControlsPage /> },
      { path: "reports", element: <ReportsPage /> },
    ],
  },
  { path: "/gallery", element: <GalleryPage /> },
  { path: "*", element: <NotFoundPage /> },
])
