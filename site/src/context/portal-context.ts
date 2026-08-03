import { createContext } from 'react'
import type { Catalog, Release } from '../types'

export interface PortalContextValue {
  catalog: Catalog
  release: Release
  topology: unknown
}

export const PortalContext = createContext<PortalContextValue | null>(null)
