import type { Catalog, Indicator, MetricKind, MunicipalitySummaryItem, MunicipalitySummaryPayload, MunicipalSeriesPayload, Release, ShareFormat, ShareRoute, ShareTemplate } from '../src/types'
import { buildCanonicalPath } from '../src/lib/share'
import { feature } from 'topojson-client'

const TEMPLATES = new Set<ShareTemplate>(['answer', 'evolution', 'map'])
const TEMPLATE_ALIASES: Record<string, ShareTemplate> = {
  resposta: 'answer',
  evolucao: 'evolution',
  mapa: 'map',
}
const FORMATS = new Set<ShareFormat>(['og', 'feed', 'story'])
const ROUTES = new Set<ShareRoute>(['municipality', 'explorer', 'profile', 'indicator'])
const METRICS = new Set<MetricKind>(['count', 'crude_rate_per_100k', 'age_sex_standardized_rate_per_100k'])

export interface SafeShareRequest { municipalityCode?: string; indicatorId: string; period?: string; metricKind?: MetricKind; template: ShareTemplate; format: ShareFormat; route?: ShareRoute; releaseId?: string }
export interface SafeShareModel extends SafeShareRequest { indicator: Indicator; municipalityName?: string; item?: MunicipalitySummaryItem; release: Release; canonicalUrl: string; values: Array<{ period: string; value: number | null }> }

async function json<T>(origin: string, path: string): Promise<T> {
  const response = await fetch(new URL(path, origin), { headers: { accept: 'application/json' } })
  if (!response.ok) throw new Error('public_artifact_unavailable')
  return response.json() as Promise<T>
}

export function parseShareRequest(url: URL): SafeShareRequest | null {
  const rawTemplate = url.searchParams.get('modelo') ?? ''
  const template = (TEMPLATE_ALIASES[rawTemplate] ?? rawTemplate) as ShareTemplate
  const format = url.searchParams.get('formato') as ShareFormat
  const indicatorId = url.searchParams.get('indicador') ?? ''
  const municipalityCode = url.searchParams.get('municipio') ?? undefined
  const period = url.searchParams.get('periodo') ?? undefined
  const metricKind = (url.searchParams.get('metrica') ?? undefined) as MetricKind | undefined
  const route = (url.searchParams.get('rota') ?? undefined) as ShareRoute | undefined
  const releaseId = url.searchParams.get('release') ?? undefined
  if (!TEMPLATES.has(template) || !FORMATS.has(format) || !/^[a-z0-9-]+$/.test(indicatorId)) return null
  if (municipalityCode && !/^33\d{5}$/.test(municipalityCode)) return null
  if (period && !/^\d{4}(?:-\d{4})?$/.test(period)) return null
  if (metricKind && !METRICS.has(metricKind)) return null
  if (route && !ROUTES.has(route)) return null
  if (releaseId && !/^[a-zA-Z0-9._-]{1,64}$/.test(releaseId)) return null
  return { template, format, indicatorId, municipalityCode, period, metricKind, route, releaseId }
}

export async function resolveShareModel(requestUrl: URL): Promise<SafeShareModel | null> {
  const parsed = parseShareRequest(requestUrl); if (!parsed) return null
  const origin = requestUrl.origin
  const [catalog, release] = await Promise.all([json<Catalog>(origin, '/data/catalog.json'), json<Release>(origin, '/data/release.json')])
  const indicator = catalog.indicators.find((item) => item.id === parsed.indicatorId); if (!indicator) return null
  let municipalityName: string | undefined
  let item: MunicipalitySummaryItem | undefined
  if (parsed.municipalityCode) {
    const summary = await json<MunicipalitySummaryPayload>(origin, `/data/municipality-summaries/${parsed.municipalityCode}.json`)
    if (summary.municipalityCode !== parsed.municipalityCode) return null
    item = summary.items.find((entry) => entry.indicatorId === indicator.id)
    try {
      const topology = await json<{ type: 'Topology'; objects: Record<string, object>; arcs: unknown[] }>(origin, '/data/geography/rj.topojson')
      const object = Object.values(topology.objects)[0]
      const collection = feature(topology as never, object as never) as unknown as { features: Array<{ properties?: Record<string, unknown> }> }
      const match = collection.features.find((entry) => String(entry.properties?.code ?? entry.properties?.CD_MUN ?? entry.properties?.id) === parsed.municipalityCode)
      municipalityName = String(match?.properties?.name ?? match?.properties?.NM_MUN ?? '') || undefined
    } catch { municipalityName = undefined }
  }
  const values: Array<{ period: string; value: number | null }> = []
  if (parsed.template === 'evolution' && parsed.municipalityCode) {
    const series = await json<MunicipalSeriesPayload>(origin, `/data/municipal-series/${indicator.id}.json`)
    series.observations.filter((entry) => entry.geographyId === parsed.municipalityCode && entry.metricKind === (parsed.metricKind ?? 'crude_rate_per_100k')).forEach((entry) => values.push({ period: entry.period, value: entry.suppressed ? null : entry.value }))
  }
  const canonicalUrl = new URL(buildCanonicalPath(parsed), origin).toString()
  return { ...parsed, indicator, municipalityName: municipalityName ?? (parsed.municipalityCode ? `Município ${parsed.municipalityCode}` : undefined), item, release, canonicalUrl, values }
}

export function metricName(metric?: MetricKind) {
  if (metric === 'count') return 'Contagem'
  if (metric === 'age_sex_standardized_rate_per_100k') return 'Taxa padronizada por idade e sexo por 100 mil'
  return 'Taxa bruta por 100 mil'
}

export function safeValue(model: SafeShareModel) {
  if (!model.item || model.item.suppressionStatus !== 'published' || model.item.value === null) return 'Dado protegido ou indisponível'
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(model.item.value)
}

export function cardSize(format: ShareFormat) { return format === 'feed' ? { width: 1080, height: 1350 } : format === 'story' ? { width: 1080, height: 1920 } : { width: 1200, height: 630 } }

export function lineSegments(values: Array<{ period: string; value: number | null }>, width = 760, height = 180) {
  const valid = values.filter((item) => item.value !== null); if (!valid.length) return []
  const years = values.map((item) => Number(item.period)); const minYear = Math.min(...years); const maxYear = Math.max(...years)
  const nums = valid.map((item) => item.value as number); const min = Math.min(...nums); const max = Math.max(...nums)
  const point = (item: { period: string; value: number | null }) => `${((Number(item.period) - minYear) / Math.max(1, maxYear - minYear)) * width},${height - (((item.value as number) - min) / Math.max(1, max - min)) * height}`
  const segments: string[] = []; let current: string[] = []; let previous: number | null = null
  values.forEach((item) => { const year = Number(item.period); if (item.value === null || (previous !== null && year !== previous + 1)) { if (current.length) segments.push(`M ${current.join(' L ')}`); current = [] } if (item.value !== null) { current.push(point(item)); previous = year } else previous = null })
  if (current.length) segments.push(`M ${current.join(' L ')}`)
  return segments
}
