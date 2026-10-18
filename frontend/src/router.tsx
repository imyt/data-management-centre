import { createBrowserRouter, Navigate } from "react-router"

import { GalleryPage } from "@/features/gallery/gallery-page"
import { NotFoundPage } from "@/features/not-found/not-found-page"

export const router = createBrowserRouter([
  // No feature screens yet; land on the gallery until the first slice ships.
  { path: "/", element: <Navigate to="/gallery" replace /> },
  { path: "/gallery", element: <GalleryPage /> },
  { path: "*", element: <NotFoundPage /> },
])
