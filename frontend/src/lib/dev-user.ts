// Dev authentication (ADR 0007): the persona the user chose in the account menu, sent on every API
// request as X-DMC-Dev-User. The backend ignores nothing silently: in oidc mode it never reads it,
// and /api/v1/dev/users answers 404, so the switcher stays hidden.
export const DEV_USER_HEADER = "X-DMC-Dev-User"

const STORAGE_KEY = "dmc-dev-user"

function storage(): Storage | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

/** The chosen persona's username, or null to act as the backend's default persona. */
export function getDevUser(): string | null {
  return storage()?.getItem(STORAGE_KEY) || null
}

export function setDevUser(username: string | null): void {
  if (username) storage()?.setItem(STORAGE_KEY, username)
  else storage()?.removeItem(STORAGE_KEY)
}

/** `fetch` for the generated client: adds the chosen persona's header to each request. */
export function fetchAsDevUser(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const request = new Request(input, init)
  const username = getDevUser()
  if (username) request.headers.set(DEV_USER_HEADER, username)
  return globalThis.fetch(request)
}
