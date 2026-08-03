import { Activity, ArrowDownRight, ArrowUpRight, Equal } from 'lucide-react'
import { deriveSeriesInsight, deriveSeriesSummary } from '../lib/seriesInsights'
import { formatMetric } from '../lib/format'
import type { Observation } from '../types'

interface SeriesInsightsProps {
  municipalityName: string
  observations: Observation[]
}

function percent(value: number | null) {
  if (value === null) return '—'
  return `${Math.abs(value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
}

function comparison(value: number | null, reference: string) {
  if (value === null) return 'Comparação indisponível'
  if (Math.abs(value) < 5) return `Próximo ${reference}`
  return `${percent(value)} ${value > 0 ? 'acima' : 'abaixo'} ${reference}`
}

function ChangeIcon({ value }: { value: number }) {
  if (Math.abs(value) < 5) return <Equal aria-hidden="true" />
  return value > 0 ? <ArrowUpRight aria-hidden="true" /> : <ArrowDownRight aria-hidden="true" />
}

export function SeriesInsights({ municipalityName, observations }: SeriesInsightsProps) {
  const insight = deriveSeriesInsight(observations)
  const summary = deriveSeriesSummary(observations)
  if (!summary) return null
  if (!insight) return (
    <section className="series-insights series-insights--compact" aria-labelledby="series-insights-title">
      <div className="series-insights__intro">
        <span>Leitura da série</span>
        <h2 id="series-insights-title">O que os anos disponíveis mostram?</h2>
        <p>Comparação descritiva de taxas brutas. Anos ausentes não são estimados.</p>
      </div>
      <div className="series-insight">
        <ChangeIcon value={summary.periodChange} />
        <span>{summary.previous.period} → {summary.latest.period}</span>
        <strong>{comparison(summary.periodChange, `de ${summary.previous.period}`)}</strong>
        <small>{formatMetric(summary.previous.value, 'crude_rate_per_100k')} → {formatMetric(summary.latest.value, 'crude_rate_per_100k')} por 100 mil</small>
      </div>
      <div className="series-insight">
        <Activity aria-hidden="true" />
        <span>Restante do RJ · {summary.latest.period}</span>
        <strong>{comparison(summary.restDifference, 'do restante do RJ')}</strong>
        <small>Comparador exclui {municipalityName}</small>
      </div>
      <div className="series-insight">
        <Activity aria-hidden="true" />
        <span>Brasil · {summary.latest.period}</span>
        <strong>{comparison(summary.brazilDifference, 'do Brasil')}</strong>
        <small>Anos publicados: {summary.availablePeriods.join(', ')}</small>
      </div>
    </section>
  )
  return (
    <section className="series-insights" aria-labelledby="series-insights-title">
      <div className="series-insights__intro">
        <span>Leitura da série</span>
        <h2 id="series-insights-title">O que mudou em {municipalityName}?</h2>
        <p>Comparação descritiva de taxas brutas. Mudanças não demonstram causa.</p>
      </div>
      <div className="series-insight">
        <ChangeIcon value={insight.pandemicChange} />
        <span>2020–2021 vs. 2018–2019</span>
        <strong>{comparison(insight.pandemicChange, 'do período anterior')}</strong>
        <small>{formatMetric(insight.pandemic, 'crude_rate_per_100k')} vs. {formatMetric(insight.baseline, 'crude_rate_per_100k')} por 100 mil</small>
      </div>
      <div className="series-insight">
        <ChangeIcon value={insight.recoveryChange} />
        <span>Último ano definitivo · {insight.latest.period}</span>
        <strong>{comparison(insight.recoveryChange, 'de 2020–2021')}</strong>
        <small>{formatMetric(insight.latest.value, 'crude_rate_per_100k')} por 100 mil</small>
      </div>
      <div className="series-insight">
        <Activity aria-hidden="true" />
        <span>Comparação territorial · {insight.latest.period}</span>
        <strong>{comparison(insight.restDifference, 'do restante do RJ')}</strong>
        <small>{comparison(insight.brazilDifference, 'do Brasil')}</small>
      </div>
      {insight.provisional ? <p className="series-insights__provisional">2025 provisório: {formatMetric(insight.provisional.value, 'crude_rate_per_100k')} por 100 mil. Não substitui o último ano definitivo.</p> : null}
    </section>
  )
}
