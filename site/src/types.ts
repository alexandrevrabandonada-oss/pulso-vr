export type Theme = 'respiratory' | 'cancer'
export type MetricKind = 'crude_rate_per_100k' | 'count'

export interface Indicator {
  id: string
  source: 'SIH' | 'SIM'
  outcomeId: string
  label: string
  theme: Theme
  measure: 'hospitalization' | 'mortality'
  measureLabel: string
  definition: string
  unit: string
  sourceLabel: string
  cidRanges: string[]
  availableMetrics: MetricKind[]
  geographyIds: string[]
  yearStart: number
  yearEnd: number
  standardization: string
  mapStatus: string
  allowsConclusion: string
  doesNotAllowConclusion: string
}

export interface Catalog {
  schemaVersion: string
  geographies: Record<string, string>
  indicators: Indicator[]
  futureCapabilities: string[]
}

export interface Observation {
  source: 'SIH' | 'SIM'
  outcomeId: string
  geographyId: string
  period: string
  metricKind: string
  value: number | null
  count: number | null
  denominator: number
  ciLow: number | null
  ciHigh: number | null
  dataStatus: string
  periodStatus: string
  manifestRef: string
  suppressed: boolean
  suppressionReason: string | null
}

export interface ProfileObservation extends Observation {
  ageGroup: string
  sex: string
}

export interface SeriesPayload {
  schemaVersion: string
  indicatorId: string
  observations: Observation[]
}

export interface ProfilePayload {
  schemaVersion: string
  indicatorId: string
  observations: ProfileObservation[]
}

export interface Release {
  schemaVersion: string
  releaseId: string
  generatedAt: string
  status: string
  smallCellThreshold: number
  primaryComparator: string
  secondaryComparator: string
  publicationGate: Record<string, string>
  coverage: {
    indicatorCount: number
    respiratoryStart: number
    cancerStart: number
    latestObservedYear: number
    missingDenominatorYears: number[]
  }
  notes: string[]
  artifacts: Array<{ path: string; bytes: number; sha256: string }>
}

export interface MapFeatureProperties {
  code: string
  name: string
  isVoltaRedonda: boolean
}
