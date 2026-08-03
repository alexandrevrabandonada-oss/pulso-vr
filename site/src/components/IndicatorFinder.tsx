import { ArrowRight, Search } from 'lucide-react'
import { FormEvent, useMemo, useState } from 'react'
import type { Indicator } from '../types'

const QUICK_INDICATORS = [
  'sim-lung',
  'sih-pneumonia',
  'sim-all-malignant-neoplasms',
  'sim-acute-myocardial-infarction',
]

function normalize(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

interface IndicatorFinderProps {
  indicators: Indicator[]
  onSelect: (indicatorId: string) => void
}

export function IndicatorFinder({ indicators, onSelect }: IndicatorFinderProps) {
  const [query, setQuery] = useState('')
  const matches = useMemo(() => {
    const term = normalize(query.trim())
    if (!term) return []
    return indicators.filter((indicator) => normalize(
      `${indicator.label} ${indicator.measureLabel} ${indicator.sourceLabel} ${indicator.theme}`,
    ).includes(term)).slice(0, 6)
  }, [indicators, query])
  const quickIndicators = useMemo(
    () => QUICK_INDICATORS.map((id) => indicators.find((indicator) => indicator.id === id)).filter((indicator): indicator is Indicator => Boolean(indicator)),
    [indicators],
  )
  const select = (indicatorId: string) => {
    setQuery('')
    onSelect(indicatorId)
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (matches[0]) select(matches[0].id)
  }

  return (
    <section className="indicator-finder" aria-labelledby="indicator-finder-title">
      <div className="indicator-finder__intro">
        <span>Comece por aqui</span>
        <div>
          <h2 id="indicator-finder-title">O que você quer consultar?</h2>
          <p>Busque uma doença ou escolha um dos assuntos mais procurados.</p>
        </div>
      </div>
      <form className="indicator-search" onSubmit={submit} role="search">
        <Search aria-hidden="true" />
        <label className="sr-only" htmlFor="indicator-search">Buscar doença ou indicador</label>
        <input
          id="indicator-search"
          type="search"
          value={query}
          placeholder="Ex.: câncer de pulmão, pneumonia, infarto…"
          autoComplete="off"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" disabled={!matches.length}>Ver resultado <ArrowRight /></button>
      </form>
      {query.trim() ? (
        <div className="indicator-results" aria-live="polite">
          {matches.length ? matches.map((indicator) => (
            <button type="button" key={indicator.id} onClick={() => select(indicator.id)}>
              <span>{indicator.label}</span>
              <small>{indicator.measureLabel} · {indicator.sourceLabel}</small>
              <ArrowRight aria-hidden="true" />
            </button>
          )) : <p>Nenhum indicador encontrado. Tente “pulmão”, “pneumonia” ou “infarto”.</p>}
        </div>
      ) : (
        <div className="indicator-shortcuts" aria-label="Assuntos em destaque">
          {quickIndicators.map((indicator) => (
            <button type="button" key={indicator.id} onClick={() => select(indicator.id)}>
              <span>{indicator.label}</span>
              <small>{indicator.measureLabel}</small>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
