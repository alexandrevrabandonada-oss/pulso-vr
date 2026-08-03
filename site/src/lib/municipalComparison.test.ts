import { describe, expect, it } from 'vitest'
import { buildMunicipalComparisonSeries, rateRatio, relativeDifferenceLabel, restOfStateExcludingMunicipality } from './municipalComparison'
import type { MapValue, Observation } from '../types'

const municipality = { count: 100, denominator: 200_000, value: 50, suppressed: false } as MapValue
const state = { count: 1_000, denominator: 2_000_000, value: 50 } as Observation

describe('municipal comparisons', () => {
  it('subtracts the selected municipality from the state aggregate', () => {
    expect(restOfStateExcludingMunicipality(municipality, state)).toEqual({
      count: 900,
      denominator: 1_800_000,
      value: 50,
    })
  })

  it('does not reconstruct a comparator from a suppressed municipal cell', () => {
    expect(restOfStateExcludingMunicipality({ ...municipality, suppressed: true, count: null }, state)).toBeNull()
  })

  it('returns a rate ratio only for valid rates', () => {
    expect(rateRatio(75, 50)).toBe(1.5)
    expect(rateRatio(75, 0)).toBeNull()
  })

  it('translates ratios into plain-language differences', () => {
    expect(relativeDifferenceLabel(0.61)).toBe('39% abaixo')
    expect(relativeDifferenceLabel(1.24)).toBe('24% acima')
    expect(relativeDifferenceLabel(1.004)).toBe('Taxa semelhante')
    expect(relativeDifferenceLabel(null)).toBe('Comparação indisponível')
  })

  it('builds a city, rest-of-state and Brazil series without exposing suppressed counts', () => {
    const municipal = [{ ...municipality, geographyId: '3300100', period: '2022' }] as MapValue[]
    const aggregates = [
      { ...state, geographyId: 'rj_total', period: '2022' },
      { ...state, geographyId: 'brazil_total', period: '2022' },
    ] as Observation[]
    const result = buildMunicipalComparisonSeries('3300100', municipal, aggregates)
    expect(result.map((item) => item.geographyId)).toEqual(['selected_municipality', 'rest_of_rj_excluding_selected', 'brazil_total'])
    expect(result[1].count).toBe(900)
  })
})
