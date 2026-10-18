import { useQuery } from "@tanstack/react-query"
import { CONTRACT_HASH } from "virtual:dmc-contract"

import { getMetaOptions } from "@/api/@tanstack/react-query.gen"
import { comparePairing, type Pairing } from "@/lib/pairing"

/** Asks the API which environment and contract it serves (ADR 0004 §5); checks again on window focus. */
export function usePairing(): Pairing {
  const { data } = useQuery({ ...getMetaOptions(), staleTime: 60_000 })
  return comparePairing(CONTRACT_HASH, data)
}
