export type Theme = 'respiratory' | 'cardiovascular' | 'cardiorespiratory' | 'cancer'
export type MetricKind = 'crude_rate_per_100k' | 'count'
export type SuppressionStatus = 'published' | 'suppressed' | 'aggregated' | 'unavailable'

export interface CoverageSummary {
  municipalityCount: number
  publishableMunicipalityCount: number
  firstPeriod: string | null
  lastPeriod: string | null
  periods: string[]
  missingPeriods: string[]
  provisionalPeriods: string[]
}

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
  municipalPeriods?: string[]
  standardization: string
  mapStatus: string
  profileAvailability?: 'available_2022_sim_age_sex' | 'not_applicable_current_release' | string
  allowsConclusion: string
  doesNotAllowConclusion: string
  synonyms?: string[]
  geographicCoverage?: Pick<CoverageSummary, 'municipalityCount' | 'publishableMunicipalityCount'>
  temporalCoverage?: Omit<CoverageSummary, 'municipalityCount' | 'publishableMunicipalityCount'>
  profileCoverage?: {
    status: 'available' | 'pilot' | 'unavailable'
    municipalityCount: number
    publishableMunicipalityCount: number
    periods: string[]
    ageGroups: string[]
    sexes: string[]
    unavailableReason?: string | null
  }
  comparisonAvailability?: { restOfState: boolean; brazil: boolean; reason?: string }
  updatedAt?: string
  methodologyUrl?: string
}

export interface Catalog {
  schemaVersion: string
  geographies: Record<string, string>
  indicators: Indicator[]
  futureCapabilities: string[]
  discovery?: { generatedAt: string; municipalityCount: number }
}

export interface MunicipalitySummaryItem {
  indicatorId: string
  period: string | null
  value: number | null
  count: number | null
  unit: string
  dataStatus: string
  suppressionStatus: SuppressionStatus
  restOfStateValue: number | null
  brazilValue: number | null
  comparisonAvailable: boolean
  unavailableReason?: string | null
}

export interface MunicipalitySummaryPayload {
  schemaVersion: string
  generatedAt: string
  municipalityCode: string
  items: MunicipalitySummaryItem[]
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
  suppressionStatus?: SuppressionStatus
}

export interface ProfileObservation {
  municipalityCode: string
  indicatorId: string
  period: string
  ageGroup: string
  sex: string
  count: number | null
  denominator: number | null
  ratePer100k: number | null
  ciLow: number | null
  ciHigh: number | null
  suppressionStatus: 'published' | 'suppressed' | 'not_applicable' | 'unavailable'
  dataStatus: string
  manifestRef: string
}

export interface SeriesPayload {
  schemaVersion: string
  indicatorId: string
  observations: Observation[]
}

export interface MunicipalSeriesPayload extends SeriesPayload {
  periods: string[]
  note: string
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
  mapScale?: { domain: [number, number] | null; method: 'fixed_indicator_metric'; unit: string; temporalPolicy: 'comparable_across_available_periods' }
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
