import { defineConfig } from "@hey-api/openapi-ts"

// Generates src/api/ from the committed contract. Run `npm run api:sync`; never edit src/api/ by hand.
export default defineConfig({
  input: "../contracts/openapi.json",
  output: "src/api",
  plugins: [
    { name: "@hey-api/client-fetch", runtimeConfigPath: "./src/lib/api-config" },
    "@hey-api/typescript",
    "@hey-api/sdk",
  ],
})
