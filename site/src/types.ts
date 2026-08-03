export type Theme = 'respiratory' | 'cardiovascular' | 'cardiorespiratory' | 'cancer'
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
  profileAvailability?: 'available_2022_sim_age_sex' | 'not_applicable_current_release' | string
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

export interface MapValue {
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

export interface MapPayload {
  schemaVersion: string
  indicatorId: string
  status: string
  period?: string
  values: MapValue[]
  note: string
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
    cardiovascularStart?: number
    cardiorespiratoryStart?: number
    cancerStart: number
    latestObservedYear: number
    missingDenominatorYears: number[]
  }
  notes: string[]
  readiness?: {
    status: string
    publicationAllowed: boolean
    blockerCount: number
    warningCount: number
    indicatorCount: number
    observations: number
    suppressedObservations: number
    profileObservations?: number
    profileEligibleIndicators?: number
    mapValues: number
    sihIndicators: number
    sihWithBrazilComparator: number
    missingDenominatorYears: number[]
    checkedAt: string
  }
  artifacts: Array<{ path: string; bytes: number; sha256: string }>
}

export interface MapFeatureProperties {
  code: string
  name: string
  isVoltaRedonda: boolean
}
