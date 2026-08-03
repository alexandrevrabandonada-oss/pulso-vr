import type { MetricKind } from '../types'

const integer = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export function formatMetric(value: number | null, metric: MetricKind): string {
  if (value === null) return '—'
  return metric === 'count' ? integer.format(value) : decimal.format(value)
}

export function metricLabel(metric: MetricKind): string {
  if (metric === 'count') return 'Contagens registradas'
  return metric === 'age_sex_standardized_rate_per_100k'
    ? 'Taxa padronizada por idade e sexo por 100 mil habitantes'
    : 'Taxa bruta por 100 mil habitantes'
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    provisional: 'Provisório',
    source_observed: 'Observado na fonte',
    complete_annual: 'Ano completo',
    respiratory_pandemic: 'Período pandêmico',
    cardiovascular_pandemic_context: 'Contexto pandêmico',
    cardiovascular_provisional: 'Provisório',
    cardiorespiratory_pandemic_context: 'Contexto pandêmico',
    cardiorespiratory_provisional: 'Provisório',
    cancer_care_disruption: 'Interrupção assistencial',
  }
  return labels[status] ?? status.replaceAll('_', ' ')
}
