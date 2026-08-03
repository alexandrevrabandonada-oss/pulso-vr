import type { MetricKind, Observation } from '../types'

interface DownloadOptions {
  indicatorId: string
  metric: MetricKind
  geographies: string[]
  startYear: number
  endYear: number
}

const COLUMNS = [
  'indicatorId', 'source', 'outcomeId', 'geographyId', 'period', 'selectedMetricKind',
  'selectedValue', 'ratePer100k', 'count', 'denominator', 'ciLow', 'ciHigh',
  'dataStatus', 'periodStatus', 'suppressed', 'manifestRef',
] as const

function csvCell(value: unknown) {
  if (value == null) return ''
  let text = String(value)
  if (/^[=+\-@]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function buildFilteredSeriesCsv(observations: Observation[], options: DownloadOptions) {
  const allowedGeographies = new Set(options.geographies)
  const rows = observations
    .filter((item) => allowedGeographies.has(item.geographyId))
    .filter((item) => Number(item.period) >= options.startYear && Number(item.period) <= options.endYear)
    .sort((a, b) => Number(a.period) - Number(b.period) || a.geographyId.localeCompare(b.geographyId))
    .map((item) => {
      const selectedValue = options.metric === 'count' ? item.count : item.value
      return [
        options.indicatorId, item.source, item.outcomeId, item.geographyId, item.period,
        options.metric, selectedValue, item.value, item.count, item.denominator, item.ciLow,
        item.ciHigh, item.dataStatus, item.periodStatus, item.suppressed, item.manifestRef,
      ]
    })
  return `\uFEFF${COLUMNS.join(',')}\r\n${rows.map((row) => row.map(csvCell).join(',')).join('\r\n')}\r\n`
}

export function saveCsvFile(filename: string, csv: string) {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}
