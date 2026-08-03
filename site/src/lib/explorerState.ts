import type { Indicator, MetricKind, Theme } from '../types'

const THEMES = new Set<Theme>(['respiratory', 'cardiovascular', 'cardiorespiratory', 'cancer', 'neurological'])
const METRICS = new Set<MetricKind>(['crude_rate_per_100k', 'age_sex_standardized_rate_per_100k', 'count'])
const TERRITORIES = new Set(['all', 'volta_redonda', 'rest_of_rj_excluding_vr', 'brazil_total'])

export interface ExplorerState {
  indicator: Indicator
  theme: Theme
  metric: MetricKind
  territory: string
  municipalityCode: string | null
  mapPeriod: string | null
  startYear: number
  endYear: number
}

function boundedYear(value: string | null, fallback: number, minimum: number, maximum: number) {
  if (value === null) return fallback
  const parsed = Number(value)
  if (!Number.isInteger(parsed)) return fallback
  return Math.min(maximum, Math.max(minimum, parsed))
}

export function deriveExplorerState(search: string, indicators: Indicator[]): ExplorerState {
  if (!indicators.length) throw new Error('O catálogo não contém indicadores públicos.')
  const params = new URLSearchParams(search)
  const requestedTheme = params.get('tema') as Theme | null
  const validTheme = requestedTheme && THEMES.has(requestedTheme) ? requestedTheme : null
  const requestedIndicator = indicators.find((item) => item.id === params.get('indicador'))
  const indicator = requestedIndicator
    ?? (validTheme ? indicators.find((item) => item.theme === validTheme) : undefined)
    ?? indicators.find((item) => item.id === 'sih-resp-all')
    ?? indicators[0]
  const requestedMetric = params.get('medida') as MetricKind | null
  const metric = requestedMetric && METRICS.has(requestedMetric) && indicator.availableMetrics.includes(requestedMetric)
    ? requestedMetric
    : indicator.availableMetrics[0] ?? 'crude_rate_per_100k'
  const requestedTerritory = params.get('territorio')
  const territory = requestedTerritory && TERRITORIES.has(requestedTerritory) ? requestedTerritory : 'all'
  const requestedMunicipality = params.get('municipio')
  const municipalityCode = requestedMunicipality && /^\d{7}$/.test(requestedMunicipality) ? requestedMunicipality : null
  const requestedMapPeriod = params.get('ano_mapa')
  const mapPeriod = requestedMapPeriod && /^\d{4}$/.test(requestedMapPeriod) ? requestedMapPeriod : null
  let startYear = boundedYear(params.get('inicio'), indicator.yearStart, indicator.yearStart, indicator.yearEnd)
  let endYear = boundedYear(params.get('fim'), indicator.yearEnd, indicator.yearStart, indicator.yearEnd)
  if (startYear > endYear) [startYear, endYear] = [endYear, startYear]
  return { indicator, theme: indicator.theme, metric, territory, municipalityCode, mapPeriod, startYear, endYear }
}

export function explorerStateSearch(state: ExplorerState) {
  const params = new URLSearchParams({
    tema: state.theme,
    indicador: state.indicator.id,
    territorio: state.territory,
    medida: state.metric,
    inicio: String(state.startYear),
    fim: String(state.endYear),
  })
  if (state.municipalityCode) params.set('municipio', state.municipalityCode)
  if (state.mapPeriod) params.set('ano_mapa', state.mapPeriod)
  return params.toString()
}
