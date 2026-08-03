import { describe, expect, it } from 'vitest'
import type { Observation } from '../types'
import { buildFilteredSeriesCsv } from './publicDownload'

const base: Observation = {
  source: 'SIM', outcomeId: 'lung', geographyId: 'volta_redonda', period: '2022',
  metricKind: 'crude_rate_per_100k', value: 12.5, count: 30, denominator: 240000,
  ciLow: 8.4, ciHigh: 17.8, dataStatus: 'source_observed', periodStatus: 'observed',
  manifestRef: 'manifest.json', suppressed: false, suppressionReason: null,
}

describe('buildFilteredSeriesCsv', () => {
  it('contains only the selected territory and period', () => {
    const csv = buildFilteredSeriesCsv([
      base,
      { ...base, geographyId: 'brazil_total', count: 32000 },
      { ...base, period: '2021' },
    ], { indicatorId: 'sim-lung', metric: 'count', geographies: ['volta_redonda'], startYear: 2022, endYear: 2022 })
    expect(csv).toContain('volta_redonda,2022,count,30')
    expect(csv).not.toContain('brazil_total')
    expect(csv).not.toContain(',2021,')
  })

  it('does not reconstruct a suppressed value', () => {
    const csv = buildFilteredSeriesCsv([
      { ...base, value: null, count: null, ciLow: null, ciHigh: null, suppressed: true },
    ], { indicatorId: 'sim-lung', metric: 'count', geographies: ['volta_redonda'], startYear: 2022, endYear: 2022 })
    expect(csv).toContain('count,,,')
    expect(csv).toContain(',true,manifest.json')
  })
})
