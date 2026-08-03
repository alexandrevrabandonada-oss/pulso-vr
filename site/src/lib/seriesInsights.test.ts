import { describe, expect, it } from 'vitest'
import type { Observation } from '../types'
import { deriveSeriesInsight, describeDirection } from './seriesInsights'

const point = (geographyId: string, period: string, value: number, dataStatus = 'source_observed') => ({
  geographyId, period, value, dataStatus, count: 10, denominator: 100_000,
  suppressed: false, ciLow: null, ciHigh: null,
} as Observation)

describe('series insights', () => {
  it('separates the pre-pandemic baseline, pandemic period and latest definitive year', () => {
    const observations = [
      point('selected_municipality', '2018', 100), point('selected_municipality', '2019', 100),
      point('selected_municipality', '2020', 80), point('selected_municipality', '2021', 80),
      point('selected_municipality', '2024', 120), point('selected_municipality', '2025', 140, 'provisional'),
      point('rest_of_rj_excluding_selected', '2024', 100), point('brazil_total', '2024', 150),
    ]
    const insight = deriveSeriesInsight(observations)!
    expect(insight.pandemicChange).toBeCloseTo(-20)
    expect(insight.recoveryChange).toBeCloseTo(50)
    expect(insight.latest.period).toBe('2024')
    expect(insight.provisional?.period).toBe('2025')
  })

  it('uses neutral language for small changes', () => {
    expect(describeDirection(3)).toBe('estável em relação a')
    expect(describeDirection(-8)).toBe('abaixo de')
  })
})
