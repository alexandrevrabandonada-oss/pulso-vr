import type { Observation } from '../types'

export interface SeriesInsight {
  baseline: number
  pandemic: number
  latest: Observation
  pandemicChange: number
  recoveryChange: number
  restDifference: number | null
  brazilDifference: number | null
  first: Observation
  longTermChange: number
  provisional: Observation | null
}

function average(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function percentChange(value: number, reference: number) {
  return reference > 0 ? (value / reference - 1) * 100 : 0
}

export function deriveSeriesInsight(observations: Observation[]): SeriesInsight | null {
  const selected = observations
    .filter((item) => item.geographyId === 'selected_municipality' && item.value !== null && !item.suppressed)
    .sort((left, right) => Number(left.period) - Number(right.period))
  const baselineValues = selected.filter((item) => ['2018', '2019'].includes(item.period)).map((item) => item.value!)
  const pandemicValues = selected.filter((item) => ['2020', '2021'].includes(item.period)).map((item) => item.value!)
  const definitive = selected.filter((item) => item.dataStatus !== 'provisional')
  const latest = definitive.at(-1)
  const first = definitive[0]
  if (baselineValues.length !== 2 || pandemicValues.length !== 2 || !latest || !first) return null
  const baseline = average(baselineValues)
  const pandemic = average(pandemicValues)
  const rest = observations.find((item) => item.geographyId === 'rest_of_rj_excluding_selected' && item.period === latest.period)
  const brazil = observations.find((item) => item.geographyId === 'brazil_total' && item.period === latest.period)
  return {
    baseline,
    pandemic,
    latest,
    first,
    pandemicChange: percentChange(pandemic, baseline),
    recoveryChange: percentChange(latest.value!, pandemic),
    restDifference: rest?.value ? percentChange(latest.value!, rest.value) : null,
    brazilDifference: brazil?.value ? percentChange(latest.value!, brazil.value) : null,
    longTermChange: percentChange(latest.value!, first.value!),
    provisional: selected.find((item) => item.dataStatus === 'provisional') ?? null,
  }
}

export function describeDirection(change: number, stableThreshold = 5) {
  if (Math.abs(change) < stableThreshold) return 'estável em relação a'
  return change > 0 ? 'acima de' : 'abaixo de'
}
