import { QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router"

import { client } from "@/api/client.gen"
import "@/index.css"
import { queryClient } from "@/lib/query-client"
import { loadRuntimeConfig } from "@/lib/runtime-config"
import { ThemeProvider } from "@/lib/theme"
import { router } from "@/router"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

const config = await loadRuntimeConfig()
if (config.apiBaseUrl) client.setConfig({ baseUrl: config.apiBaseUrl })

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <RouterProvider router={router} />
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>
)
