import type { Indicator, MunicipalitySummaryItem, Release } from '../types'

export type SeoRoute = 'home' | 'municipality' | 'indicator' | 'profiles' | 'methods' | 'data' | 'explorer' | 'not-found'

export interface SeoContext {
  origin: string
  route: SeoRoute
  pathname: string
  municipalityCode?: string
  municipalityName?: string
  indicator?: Indicator
  summary?: MunicipalitySummaryItem | null
  release: Release
}

export interface SeoMetadata {
  title: string
  description: string
  canonicalUrl: string
  robots: 'index,follow' | 'noindex,follow' | 'noindex,nofollow'
  ogImage: string
  ogImageAlt: string
  structuredData: Record<string, unknown>[]
}

const PRODUCT_NAME = 'Observatório Estadual de Saúde do RJ'
const PARTNER_NAME = 'VR Abandonada'
const PARTNER_URL = 'https://www.instagram.com/vr_abandonada/'

export function isPubliclyIndexable(release: Release) {
  return release.status === 'public_release_ready' || release.readiness?.publicationAllowed === true
}

export function routeFromPath(pathname: string, search = ''): SeoRoute {
  if (pathname === '/') return 'home'
  if (/^\/municipios\/33\d{5}$/.test(pathname)) return 'municipality'
  if (/^\/indicadores\/[a-z0-9-]+$/.test(pathname)) return 'indicator'
  if (pathname === '/perfis') return 'profiles'
  if (pathname === '/metodos') return 'methods'
  if (pathname === '/dados') return 'data'
  if (pathname === '/explorador') return 'explorer'
  void search
  return 'not-found'
}

function canonicalPath(context: SeoContext) {
  if (context.route === 'municipality' && context.municipalityCode) {
    const query = context.indicator ? `?indicador=${encodeURIComponent(context.indicator.id)}` : ''
    return `/municipios/${context.municipalityCode}${query}`
  }
  if (context.route === 'indicator' && context.indicator) return `/indicadores/${encodeURIComponent(context.indicator.id)}`
  if (context.route === 'profiles') return '/perfis'
  if (context.route === 'methods') return '/metodos'
  if (context.route === 'data') return '/dados'
  if (context.route === 'explorer') return '/explorador'
  return '/'
}

function descriptionFor(context: SeoContext) {
  if (context.route === 'home') return 'Dados públicos de saúde dos 92 municípios do Rio de Janeiro, com fontes, comparações territoriais, séries históricas e limitações visíveis.'
  if (context.route === 'municipality') {
    const name = context.municipalityName ?? 'este município'
    if (context.indicator) return `${context.indicator.label} em ${name}: definição, período, comparação com o restante do RJ e leitura metodológica no Observatório.`
    return `Visão geral de saúde de ${name}, com indicadores públicos de mortalidade e internações de residentes, fontes e limitações.`
  }
  if (context.route === 'indicator' && context.indicator) return `${context.indicator.label}: definição, fonte ${context.indicator.sourceLabel}, cobertura municipal, métricas disponíveis e limites de interpretação.`
  if (context.route === 'profiles') return 'Perfis municipais de saúde por idade e sexo, com taxas específicas, supressão e limitações de comparabilidade.'
  if (context.route === 'methods') return 'Como o Observatório adquire, valida, compara e publica dados de saúde dos municípios do Rio de Janeiro.'
  if (context.route === 'data') return 'Catálogo, séries, manifestos, downloads e regras de proveniência dos dados públicos de saúde do Rio de Janeiro.'
  if (context.route === 'explorer') return 'Explore indicadores de saúde dos municípios do Rio de Janeiro por território, tempo, população, fonte e métrica.'
  return 'Página não encontrada no Observatório Estadual de Saúde do RJ.'
}

function titleFor(context: SeoContext) {
  if (context.route === 'home') return `${PRODUCT_NAME} | Dados públicos dos 92 municípios`
  if (context.route === 'municipality') return context.indicator && context.municipalityName
    ? `${context.indicator.label} em ${context.municipalityName} | ${PRODUCT_NAME}`
    : `Saúde em ${context.municipalityName ?? 'município do RJ'} | ${PRODUCT_NAME}`
  if (context.route === 'indicator' && context.indicator) return `${context.indicator.label}: fonte, método e cobertura | ${PRODUCT_NAME}`
  if (context.route === 'profiles') return `Perfis por idade e sexo | ${PRODUCT_NAME}`
  if (context.route === 'methods') return `Fontes e métodos | ${PRODUCT_NAME}`
  if (context.route === 'data') return `Dados abertos de saúde do RJ | ${PRODUCT_NAME}`
  if (context.route === 'explorer') return `Explorador de dados | ${PRODUCT_NAME}`
  return `Página não encontrada | ${PRODUCT_NAME}`
}

function organizationJsonLd(origin: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: PRODUCT_NAME,
    url: origin,
    description: 'Portal público para leitura de dados de saúde dos 92 municípios do Rio de Janeiro.',
    sameAs: [PARTNER_URL],
    sponsor: { '@type': 'Organization', name: PARTNER_NAME, url: PARTNER_URL },
  }
}

function breadcrumbs(context: SeoContext) {
  const items: Array<Record<string, unknown>> = [{ '@type': 'ListItem', position: 1, name: 'Início', item: context.origin + '/' }]
  if (context.route === 'municipality' && context.municipalityName) items.push({ '@type': 'ListItem', position: items.length + 1, name: context.municipalityName, item: context.origin + `/municipios/${context.municipalityCode}` })
  if (context.indicator) items.push({ '@type': 'ListItem', position: items.length + 1, name: context.indicator.label, item: context.origin + `/indicadores/${context.indicator.id}` })
  if (context.route === 'methods') items.push({ '@type': 'ListItem', position: 2, name: 'Fontes e métodos', item: context.origin + '/metodos' })
  if (context.route === 'data') items.push({ '@type': 'ListItem', position: 2, name: 'Dados abertos', item: context.origin + '/dados' })
  return { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: items }
}

function datasetJsonLd(context: SeoContext) {
  if (!context.indicator) return null
  const spatialName = context.municipalityName ?? 'Municípios do estado do Rio de Janeiro'
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: context.municipalityName ? `${context.indicator.label} em ${context.municipalityName}` : context.indicator.label,
    description: descriptionFor(context),
    url: context.origin + canonicalPath(context),
    creator: { '@type': 'Organization', name: PRODUCT_NAME, url: context.origin },
    sponsor: { '@type': 'Organization', name: PARTNER_NAME, url: PARTNER_URL },
    spatialCoverage: { '@type': 'Place', name: spatialName },
    temporalCoverage: `${context.indicator.yearStart}/${context.indicator.yearEnd}`,
    variableMeasured: context.indicator.label,
    measurementTechnique: `${context.indicator.sourceLabel}; ${context.indicator.geographyBasis === 'establishment' ? 'local do estabelecimento' : 'município de residência'}`,
    isBasedOn: context.indicator.sourceLabel,
    distribution: [{ '@type': 'DataDownload', encodingFormat: 'application/json', contentUrl: context.origin + `/data/series/${context.indicator.id}.json` }],
  }
}

export function buildSeoMetadata(context: SeoContext): SeoMetadata {
  const currentCanonical = new URL(canonicalPath(context), context.origin).toString()
  const hasInvalidQuery = (context.route === 'indicator' && !context.indicator) || (context.route === 'municipality' && !context.municipalityName)
  const robots = !isPubliclyIndexable(context.release)
    ? 'noindex,nofollow'
    : context.route === 'not-found' || hasInvalidQuery
      ? 'noindex,nofollow'
      : context.route === 'explorer' || context.route === 'profiles'
        ? 'noindex,follow'
        : 'index,follow'
  const dataset = datasetJsonLd(context)
  return {
    title: titleFor(context),
    description: descriptionFor(context),
    canonicalUrl: currentCanonical,
    robots,
    ogImage: new URL('/brand/vr-abandonada.png', context.origin).toString(),
    ogImageAlt: 'VR Abandonada — realização conjunta do Observatório Estadual de Saúde do RJ',
    structuredData: [organizationJsonLd(context.origin), breadcrumbs(context), ...(dataset ? [dataset] : [])],
  }
}

export function seoContextFromBrowser(location: string, release: Release, indicators: Indicator[], municipalities: Array<{ code: string; name: string }>, summaries: Map<string, MunicipalitySummaryItem | null> = new Map()): SeoContext {
  const url = new URL(location, window.location.origin)
  const route = routeFromPath(url.pathname, url.search)
  const municipalityCode = /^\/municipios\/(33\d{5})$/.exec(url.pathname)?.[1]
  const indicatorId = route === 'indicator' ? url.pathname.split('/').pop() : url.searchParams.get('indicador')
  const indicator = indicators.find((item) => item.id === indicatorId)
  const municipality = municipalities.find((item) => item.code === municipalityCode)
  return { origin: url.origin, route, pathname: url.pathname, municipalityCode, municipalityName: municipality?.name, indicator, summary: municipalityCode ? summaries.get(municipalityCode) : undefined, release }
}

export { PARTNER_URL, PRODUCT_NAME }
