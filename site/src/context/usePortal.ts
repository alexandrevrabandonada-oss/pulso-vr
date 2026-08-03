import { useContext } from 'react'
import { PortalContext } from './portal-context'

export function usePortal() {
  const value = useContext(PortalContext)
  if (!value) throw new Error('usePortal must be used within PortalProvider')
  return value
}
