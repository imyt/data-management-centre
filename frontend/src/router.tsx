import { createBrowserRouter, Navigate } from "react-router"

import { ComponentsPage } from "@/features/gallery/components-page"

export const router = createBrowserRouter([
  // No feature screens yet; land on the gallery until the first slice ships.
  { path: "/", element: <Navigate to="/dev/components" replace /> },
  { path: "/dev/components", element: <ComponentsPage /> },
])
