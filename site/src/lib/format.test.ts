import { describe, expect, it } from 'vitest'
import { formatMetric, metricLabel } from './format'

describe('metric formatting', () => {
  it('uses an em dash for unavailable or suppressed values', () => {
    expect(formatMetric(null, 'count')).toBe('—')
  })

  it('labels crude rates explicitly', () => {
    expect(metricLabel('crude_rate_per_100k')).toContain('bruta')
  })
})
