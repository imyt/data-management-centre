import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { loadEnv } from "vite"
import { defineConfig } from "vitest/config"

export default defineConfig(({ mode }) => {
  // Not a VITE_* variable, so it never reaches the bundle (ADR 0004 §4). Set it in .env.local or the shell.
  const env = loadEnv(mode, process.cwd(), "DMC_")
  const apiTarget = env.DMC_API_PROXY_TARGET || "http://localhost:8000"

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    // The app calls the API same-origin under /api; locally the dev server forwards it to the backend.
    server: { port: 5173, strictPort: true, proxy: { "/api": { target: apiTarget, changeOrigin: true } } },
    test: { include: ["src/**/*.test.{ts,tsx}"] },
  }
})
