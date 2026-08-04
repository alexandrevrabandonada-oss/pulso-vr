import { feature } from 'topojson-client'
import type { Catalog, Release } from '../src/types'
import { buildSeoMetadata, type SeoContext, type SeoRoute } from '../src/lib/seo'

export const config = { runtime: 'edge' }

const escapeHtml = (value: string) => value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)
const safeJson = (value: unknown) => JSON.stringify(value).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')

async function json<T>(origin: string, path: string) {
  const response = await fetch(new URL(path, origin), { headers: { accept: 'application/json' } })
  if (!response.ok) throw new Error('public_artifact_unavailable')
  return response.json() as Promise<T>
}

function fallback(context: SeoContext, description: string) {
  const links = context.route === 'not-found' ? '<p><a href="/">Voltar ao início</a></p>' : '<nav><a href="/">Início</a> · <a href="/explorador">Explorador de dados</a> · <a href="/metodos">Fontes e métodos</a></nav>'
  return `<main><h1>${escapeHtml(context.route === 'not-found' ? 'Página não encontrada' : context.municipalityName ?? context.indicator?.label ?? 'Observatório Estadual de Saúde do RJ')}</h1><p>${escapeHtml(description)}</p>${links}</main>`
}

function headMarkup(metadata: ReturnType<typeof buildSeoMetadata>) {
  const meta = (name: string, content: string) => `<meta name="${name}" content="${escapeHtml(content)}">`
  const property = (name: string, content: string) => `<meta property="${name}" content="${escapeHtml(content)}">`
  const structured = metadata.structuredData.map((item) => `<script type="application/ld+json" data-observatorio-seo="true">${safeJson(item)}</script>`).join('')
  return `<title>${escapeHtml(metadata.title)}</title>${meta('description', metadata.description)}${meta('robots', metadata.robots)}${property('og:type', 'website')}${property('og:site_name', 'Observatório Estadual de Saúde do RJ')}${property('og:locale', 'pt_BR')}${property('og:title', metadata.title)}${property('og:description', metadata.description)}${property('og:url', metadata.canonicalUrl)}${property('og:image', metadata.ogImage)}${property('og:image:alt', metadata.ogImageAlt)}${meta('twitter:card', 'summary_large_image')}${meta('twitter:title', metadata.title)}${meta('twitter:description', metadata.description)}${meta('twitter:image', metadata.ogImage)}<link rel="canonical" href="${escapeHtml(metadata.canonicalUrl)}">${structured}`
}

export default async function handler(request: Request) {
  const requestUrl = new URL(request.url)
  try {
    const [catalog, release] = await Promise.all([
      json<Catalog>(requestUrl.origin, '/data/catalog.json'),
      json<Release>(requestUrl.origin, '/data/release.json'),
    ])
    const route = (requestUrl.searchParams.get('route') ?? 'not-found') as SeoRoute
    const municipalityCode = requestUrl.searchParams.get('codigo') ?? undefined
    const indicatorId = requestUrl.searchParams.get('indicador') ?? requestUrl.searchParams.get('id') ?? undefined
    const indicator = catalog.indicators.find((item) => item.id === indicatorId)
    let municipalityName: string | undefined
    if (municipalityCode) {
      const topology = await json<{ type: 'Topology'; objects: Record<string, object>; arcs: unknown[] }>(requestUrl.origin, '/data/geography/rj.topojson')
      const object = Object.values(topology.objects)[0]
      const collection = feature(topology as never, object as never) as unknown as { features: Array<{ properties?: Record<string, unknown> }> }
      const match = collection.features.find((entry) => String(entry.properties?.code ?? entry.properties?.CD_MUN ?? entry.properties?.id) === municipalityCode)
      municipalityName = String(match?.properties?.name ?? match?.properties?.NM_MUN ?? '') || undefined
    }
    const validRoute = route === 'home' || route === 'municipality' || route === 'indicator' || route === 'profiles' || route === 'methods' || route === 'data' || route === 'explorer'
    const resolvedRoute: SeoRoute = validRoute && (route !== 'indicator' || indicator) && (route !== 'municipality' || municipalityName) ? route : 'not-found'
    const pathname = route === 'municipality' && municipalityCode ? `/municipios/${municipalityCode}` : route === 'indicator' && indicator ? `/indicadores/${indicator.id}` : route === 'profiles' ? '/perfis' : route === 'methods' ? '/metodos' : route === 'data' ? '/dados' : route === 'explorer' ? '/explorador' : '/'
    const context: SeoContext = { origin: requestUrl.origin, route: resolvedRoute, pathname, municipalityCode, municipalityName, indicator, release }
    const metadata = buildSeoMetadata(context)
    const shellResponse = await fetch(new URL('/index.html', requestUrl.origin))
    if (!shellResponse.ok) throw new Error('app_shell_unavailable')
    let html = await shellResponse.text()
    html = html.replace(/<title>[\s\S]*?<\/title>/i, '').replace(/<meta name="description"[^>]*>/gi, '').replace(/<meta name="robots"[^>]*>/gi, '').replace(/<meta property="og:[^"]+"[^>]*>/gi, '').replace(/<meta name="twitter:[^"]+"[^>]*>/gi, '').replace(/<link rel="canonical"[^>]*>/gi, '').replace(/<script type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>/gi, '')
    html = html.replace('</head>', `${headMarkup(metadata)}</head>`)
    html = html.replace('<div id="root"></div>', `<div id="root">${fallback(context, metadata.description)}</div>`)
    return new Response(`<!doctype html>${html.replace(/^<!doctype html>/i, '')}`, { status: resolvedRoute === 'not-found' ? 404 : 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600' } })
  } catch (error) {
    console.error('[seo-page]', error)
    const errorCode = error instanceof Error ? error.message : 'unknown_error'
    return new Response('Página temporariamente indisponível.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow', 'X-SEO-Error': errorCode.slice(0, 80) } })
  }
}
