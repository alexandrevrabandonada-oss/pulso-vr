import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { loadPortalFoundation } from '../lib/data'
import type { Catalog, Release } from '../types'
import { ErrorState, LoadingState } from '../components/LoadingState'

interface PortalContextValue {
  catalog: Catalog
  release: Release
  topology: unknown
}

const PortalContext = createContext<PortalContextValue | null>(null)

export function PortalProvider({ children }: { children: ReactNode }) {
  const [value, setValue] = useState<PortalContextValue | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    loadPortalFoundation()
      .then(([catalog, release, topology]) => {
        if (active) setValue({ catalog, release, topology })
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : String(reason))
      })
    return () => { active = false }
  }, [])
  if (error) return <main className="page-shell"><ErrorState message={error} /></main>
  if (!value) return <main className="page-shell"><LoadingState /></main>
  return <PortalContext.Provider value={value}>{children}</PortalContext.Provider>
}

export function usePortal() {
  const value = useContext(PortalContext)
  if (!value) throw new Error('usePortal must be used within PortalProvider')
  return value
}
