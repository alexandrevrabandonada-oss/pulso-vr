import type { MetricKind } from '../types'

const integer = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export function formatMetric(value: number | null, metric: MetricKind): string {
  if (value === null) return '—'
  return metric === 'count' ? integer.format(value) : decimal.format(value)
}

export function metricLabel(metric: MetricKind): string {
  return metric === 'count' ? 'Contagens registradas' : 'Taxa bruta por 100 mil habitantes'
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    provisional: 'Provisório',
    source_observed: 'Observado na fonte',
    complete_annual: 'Ano completo',
    respiratory_pandemic: 'Período pandêmico',
    cancer_care_disruption: 'Interrupção assistencial',
  }
  return labels[status] ?? status.replaceAll('_', ' ')
}
