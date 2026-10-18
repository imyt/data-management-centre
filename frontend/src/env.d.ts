interface ImportMetaEnv {
  /** Origin of the DMC API, e.g. the backend's URL in local dev. */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
