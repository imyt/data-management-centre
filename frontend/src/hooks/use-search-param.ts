import * as React from "react"
import { useSearchParams } from "react-router"

/**
 * One query parameter as state, so selections are deep-linkable and work with back and forward.
 * Setting pushes a history entry; null removes the parameter. Other parameters are kept.
 */
export function useSearchParam(key: string) {
  const [params, setParams] = useSearchParams()
  const value = params.get(key)

  const set = React.useCallback(
    (next: string | null) => {
      setParams((prev) => {
        const out = new URLSearchParams(prev)
        if (next === null) out.delete(key)
        else out.set(key, next)
        return out
      })
    },
    [key, setParams]
  )

  return [value, set] as const
}
