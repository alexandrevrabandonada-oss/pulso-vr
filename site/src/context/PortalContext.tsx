import { useEffect, useState, type ReactNode } from 'react'
import { loadPortalFoundation } from '../lib/data'
import { ErrorState, LoadingState } from '../components/LoadingState'
import { PortalContext, type PortalContextValue } from './portal-context'

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
