import type { MapValue, Observation } from '../types'

export interface ComparableValue {
  count: number | null
  denominator: number | null
  value: number | null
}

export function restOfStateExcludingMunicipality(
  municipality: MapValue | null,
  stateTotal: Observation | null,
): ComparableValue | null {
  if (!municipality || municipality.suppressed || municipality.count === null || !stateTotal || stateTotal.count === null) return null
  const denominator = stateTotal.denominator - municipality.denominator
  const count = stateTotal.count - municipality.count
  if (denominator <= 0 || count < 0) return null
  return { count, denominator, value: count / denominator * 100_000 }
}

export function rateRatio(value: number | null | undefined, comparator: number | null | undefined) {
  if (value === null || value === undefined || comparator === null || comparator === undefined || comparator <= 0) return null
  return value / comparator
}

export function buildMunicipalComparisonSeries(
  municipalityCode: string,
  municipalObservations: Observation[],
  aggregateObservations: Observation[],
): Observation[] {
  const result: Observation[] = []
  for (const municipality of municipalObservations) {
    if (municipality.geographyId !== municipalityCode) continue
    const state = aggregateObservations.find((item) => item.geographyId === 'rj_total' && item.period === municipality.period) ?? null
    const brazil = aggregateObservations.find((item) => item.geographyId === 'brazil_total' && item.period === municipality.period)
    const rest = restOfStateExcludingMunicipality(municipality, state)
    result.push({ ...municipality, geographyId: 'selected_municipality' })
    result.push({
      ...municipality,
      geographyId: 'rest_of_rj_excluding_selected',
      value: rest?.value ?? null,
      count: rest?.count ?? null,
      denominator: rest?.denominator ?? state?.denominator ?? municipality.denominator,
      ciLow: null,
      ciHigh: null,
      suppressed: rest === null,
      suppressionReason: rest === null ? 'selected_municipality_suppressed' : null,
    })
    if (brazil) result.push(brazil)
  }
  return result
}
