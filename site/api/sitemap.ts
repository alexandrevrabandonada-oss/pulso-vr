import { feature } from 'topojson-client'
import type { Catalog, Release } from '../src/types'

export const config = { runtime: 'edge' }

async function json<T>(origin: string, path: string) {
  const response = await fetch(new URL(path, origin), { headers: { accept: 'application/json' } })
  if (!response.ok) throw new Error('public_artifact_unavailable')
  return response.json() as Promise<T>
}

const xml = (value: string) => value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[character]!)

export default async function handler(request: Request) {
  const origin = new URL(request.url).origin
  try {
    const [catalog, release, topology] = await Promise.all([
      json<Catalog>(origin, '/data/catalog.json'),
      json<Release>(origin, '/data/release.json'),
      json<{ type: 'Topology'; objects: Record<string, object>; arcs: unknown[] }>(origin, '/data/geography/rj.topojson'),
    ])
    const publicRelease = release.status === 'public_release_ready' || release.readiness?.publicationAllowed === true
    if (!publicRelease) return new Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>', { headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600' } })
    const object = Object.values(topology.objects)[0]
    const collection = feature(topology as never, object as never) as unknown as { features: Array<{ properties?: Record<string, unknown> }> }
    const lastmod = new Date(release.generatedAt).toISOString().slice(0, 10)
    const urls = new Set<string>(['/', '/metodos', '/dados', '/perfis'])
    catalog.indicators.forEach((indicator) => urls.add(`/indicadores/${indicator.id}`))
    collection.features.forEach((entry) => {
      const code = String(entry.properties?.code ?? entry.properties?.CD_MUN ?? entry.properties?.id ?? '')
      if (/^33\d{5}$/.test(code)) urls.add(`/municipios/${code}`)
    })
    const body = [...urls].sort().map((path) => `<url><loc>${xml(origin + path)}</loc><lastmod>${lastmod}</lastmod></url>`).join('')
    return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${body}</urlset>`, { headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600' } })
  } catch {
    return new Response('Sitemap temporariamente indisponível.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } })
  }
}
