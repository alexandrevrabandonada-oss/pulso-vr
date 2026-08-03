import type { Catalog, MapPayload, ProfilePayload, Release, SeriesPayload } from '../types'

const jsonCache = new Map<string, Promise<unknown>>()

async function fetchJson<T>(path: string): Promise<T> {
  if (!jsonCache.has(path)) {
    const request = fetch(path)
      .then(async (response) => {
        if (!response.ok) throw new Error(`Falha ao carregar ${path}: ${response.status}`)
        return response.json()
      })
      .catch((error) => {
        jsonCache.delete(path)
        throw error
      })
    jsonCache.set(path, request)
  }
  return jsonCache.get(path) as Promise<T>
}

export function loadPortalFoundation() {
  return Promise.all([
    fetchJson<Catalog>('/data/catalog.json'),
    fetchJson<Release>('/data/release.json'),
    fetchJson<unknown>('/data/geography/rj.topojson'),
  ])
}

export function loadSeries(indicatorId: string) {
  return fetchJson<SeriesPayload>(`/data/series/${indicatorId}.json`)
}

export function loadProfile(indicatorId: string) {
  return fetchJson<ProfilePayload>(`/data/profiles/${indicatorId}.json`)
}

export function loadMap(indicatorId: string) {
  return fetchJson<MapPayload>(`/data/maps/rj/${indicatorId}.json`)
}
