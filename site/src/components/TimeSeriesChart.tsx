import { useMemo, useState } from 'react'
import type { Indicator, MetricKind, Observation } from '../types'
import { formatMetric, metricLabel } from '../lib/format'

const COLORS: Record<string, string> = {
  volta_redonda: '#0b0b0b',
  rest_of_rj_excluding_vr: '#f2d400',
  brazil_total: '#e34b13',
  rj_total: '#6b6b60',
}

const ORDER = ['volta_redonda', 'rest_of_rj_excluding_vr', 'brazil_total']

interface ChartProps {
  indicator: Indicator
  observations: Observation[]
  metric: MetricKind
  geographyLabels: Record<string, string>
  startYear?: number
  endYear?: number
  compact?: boolean
  geographies?: string[]
}

interface Point {
  year: number
  value: number
  low: number | null
  high: number | null
  observation: Observation
}

function contiguousSegments(points: Point[]): Point[][] {
  const segments: Point[][] = []
  for (const point of points) {
    const current = segments.at(-1)
    if (!current || point.year - current.at(-1)!.year > 1) segments.push([point])
    else current.push(point)
  }
  return segments
}

export function TimeSeriesChart({
  indicator,
  observations,
  metric,
  geographyLabels,
  startYear,
  endYear,
  compact = false,
  geographies = ORDER,
}: ChartProps) {
  const [activePoint, setActivePoint] = useState<{ geography: string; point: Point } | null>(null)
  const model = useMemo(() => {
    const usable = observations.filter((item) => {
      const year = Number(item.period)
      const value = metric === 'count' ? item.count : item.value
      return value !== null && (!startYear || year >= startYear) && (!endYear || year <= endYear)
    })
    const byGeography = new Map<string, Point[]>()
    for (const observation of usable) {
      if (!geographies.includes(observation.geographyId)) continue
      const point = {
        year: Number(observation.period),
        value: Number(metric === 'count' ? observation.count : observation.value),
        low: metric === 'count' ? null : observation.ciLow,
        high: metric === 'count' ? null : observation.ciHigh,
        observation,
      }
      const values = byGeography.get(observation.geographyId) ?? []
      values.push(point)
      byGeography.set(observation.geographyId, values)
    }
    for (const values of byGeography.values()) values.sort((a, b) => a.year - b.year)
    const allPoints = [...byGeography.values()].flat()
    const minYear = startYear ?? Math.min(...allPoints.map((item) => item.year))
    const maxYear = endYear ?? Math.max(...allPoints.map((item) => item.year))
    const maxValue = Math.max(...allPoints.flatMap((item) => [item.value, item.high ?? item.value]), 1)
    return { byGeography, minYear, maxYear, maxValue }
  }, [observations, metric, startYear, endYear, geographies])

  const width = compact ? 620 : 1120
  const height = compact ? 240 : 300
  const margins = { top: 38, right: 26, bottom: 44, left: compact ? 54 : 70 }
  const innerWidth = width - margins.left - margins.right
  const innerHeight = height - margins.top - margins.bottom
  const x = (year: number) => margins.left + ((year - model.minYear) / Math.max(1, model.maxYear - model.minYear)) * innerWidth
  const y = (value: number) => margins.top + innerHeight - (value / model.maxValue) * innerHeight
  const pathFor = (points: Point[]) => points.map((point, index) => `${index ? 'L' : 'M'}${x(point.year).toFixed(1)},${y(point.value).toFixed(1)}`).join(' ')
  const ribbonFor = (points: Point[]) => {
    const upper = points.filter((point) => point.high !== null).map((point) => `${x(point.year).toFixed(1)},${y(point.high!).toFixed(1)}`)
    const lower = [...points].reverse().filter((point) => point.low !== null).map((point) => `${x(point.year).toFixed(1)},${y(point.low!).toFixed(1)}`)
    return upper.length ? `M${upper.join(' L')} L${lower.join(' L')} Z` : ''
  }
  const ticks = Array.from({ length: 5 }, (_, index) => (model.maxValue / 4) * index)
  const yearTickCount = Math.min(8, model.maxYear - model.minYear + 1)
  const yearTicks = Array.from(
    { length: yearTickCount },
    (_, index) => Math.round(model.minYear + ((model.maxYear - model.minYear) * index) / Math.max(1, yearTickCount - 1)),
  ).filter((value, index, values) => index === 0 || value !== values[index - 1])

  const markers = indicator.theme === 'cancer'
    ? [{ year: 2020, label: '2020–2022' }, { year: 2022, label: 'mar/2022' }]
    : indicator.theme === 'cardiovascular' || indicator.theme === 'cardiorespiratory'
      ? [{ year: 2020, label: '2020–2021' }]
    : [{ year: 2020, label: 'mar/2020' }]
  if (model.maxYear >= 2025) markers.push({ year: 2025, label: '2025 provisório' })
  const tableYears = [...new Set(observations
    .map((item) => Number(item.period))
    .filter((year) => (!startYear || year >= startYear) && (!endYear || year <= endYear)))]
    .sort((a, b) => a - b)

  return (
    <figure className={`time-chart${compact ? ' time-chart--compact' : ''}`}>
      <figcaption className="time-chart__heading">
        <span>Série temporal</span>
        <strong>{metricLabel(metric)}</strong>
      </figcaption>
      <div className="time-chart__legend" aria-label="Legenda dos territórios">
        {geographies.map((id) => (
          <span key={id} className={model.byGeography.has(id) ? '' : 'is-unavailable'}>
            <i style={{ background: COLORS[id] }} />
            {geographyLabels[id] ?? id}
            {model.byGeography.has(id) ? null : ' — em preparação'}
          </span>
        ))}
      </div>
      <div className="time-chart__scroller">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="series-title series-desc">
          <title id="series-title">{indicator.label}: {metricLabel(metric)}</title>
          <desc id="series-desc">Comparação temporal entre Volta Redonda, o restante do Rio de Janeiro e o Brasil quando disponível. Lacunas não são interpoladas.</desc>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={margins.left} x2={width - margins.right} y1={y(tick)} y2={y(tick)} className="chart-grid" />
              <text x={margins.left - 12} y={y(tick) + 4} textAnchor="end" className="chart-axis-label">{formatMetric(tick, metric)}</text>
            </g>
          ))}
          {yearTicks.map((year) => (
            <text key={year} x={x(year)} y={height - 15} textAnchor="middle" className="chart-axis-label">{year}</text>
          ))}
          {markers.filter((marker) => marker.year >= model.minYear && marker.year <= model.maxYear).map((marker) => (
            <g key={marker.label}>
              <line x1={x(marker.year)} x2={x(marker.year)} y1={margins.top - 8} y2={height - margins.bottom} className="chart-marker" />
              <text x={x(marker.year)} y={18} textAnchor="middle" className="chart-marker-label">{marker.label}</text>
            </g>
          ))}
          {geographies.map((geography) => {
            const points = model.byGeography.get(geography) ?? []
            return contiguousSegments(points).map((segment, segmentIndex) => (
              <g key={`${geography}-${segmentIndex}`}>
                {metric === 'crude_rate_per_100k' ? <path d={ribbonFor(segment)} fill={COLORS[geography]} className="chart-ribbon" /> : null}
                <path d={pathFor(segment)} stroke={COLORS[geography]} className="chart-line" />
              </g>
            ))
          })}
          {geographies.flatMap((geography) => (model.byGeography.get(geography) ?? []).map((point) => (
            <circle
              key={`${geography}-${point.year}`}
              cx={x(point.year)}
              cy={y(point.value)}
              r={activePoint?.geography === geography && activePoint.point.year === point.year ? 5 : 3}
              fill={COLORS[geography]}
              className="chart-point"
              tabIndex={0}
              aria-label={`${geographyLabels[geography]}, ${point.year}: ${formatMetric(point.value, metric)}`}
              onMouseEnter={() => setActivePoint({ geography, point })}
              onMouseLeave={() => setActivePoint(null)}
              onFocus={() => setActivePoint({ geography, point })}
              onBlur={() => setActivePoint(null)}
            />
          )))}
        </svg>
      </div>
      <div className="chart-live" aria-live="polite">
        {activePoint ? `${geographyLabels[activePoint.geography]}, ${activePoint.point.year}: ${formatMetric(activePoint.point.value, metric)}` : 'Passe o cursor ou use Tab nos pontos para ver valores.'}
      </div>
      {compact ? null : (
        <details className="chart-table-details">
          <summary>Ver dados em tabela</summary>
          <div className="chart-table-wrap">
            <table>
              <caption>{indicator.label} — {metricLabel(metric)}</caption>
              <thead><tr><th scope="col">Ano</th>{geographies.map((id) => <th scope="col" key={id}>{geographyLabels[id]}</th>)}</tr></thead>
              <tbody>
                {tableYears.map((year) => (
                  <tr key={year}>
                    <th scope="row">{year}</th>
                    {geographies.map((id) => {
                      const observation = observations.find((item) => item.geographyId === id && Number(item.period) === year)
                      const value = metric === 'count' ? observation?.count : observation?.value
                      return <td key={id}>{observation?.suppressed ? 'Suprimido' : value == null ? 'Sem dado' : formatMetric(value, metric)}</td>
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  )
}
