import { Download, Filter, Share2, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { trackEvent } from '../lib/analytics'
import type { Indicator, MetricKind, Theme } from '../types'

interface FilterProps {
  theme: Theme
  indicators: Indicator[]
  indicatorId: string
  metric: MetricKind
  startYear: number
  endYear: number
  onTheme: (value: Theme) => void
  onIndicator: (value: string) => void
  onMetric: (value: MetricKind) => void
  onStartYear: (value: number) => void
  onEndYear: (value: number) => void
  onDownload: () => void
}

export function ExplorerFilters(props: FilterProps) {
  const [open, setOpen] = useState(false)
  const [feedback, setFeedback] = useState('')
  const triggerRef = useRef<HTMLButtonElement>(null)
  const selected = props.indicators.find((item) => item.id === props.indicatorId)!
  const years = Array.from({ length: selected.yearEnd - selected.yearStart + 1 }, (_, index) => selected.yearStart + index)
  const share = async () => {
    const url = window.location.href
    try {
      if (navigator.share) await navigator.share({ title: 'Observatório Saúde & Ambiente', url })
      else await navigator.clipboard.writeText(url)
      setFeedback('Link pronto para compartilhar.')
    } catch (error) {
      if ((error as DOMException).name !== 'AbortError') setFeedback('Não foi possível compartilhar este link.')
    }
  }
  const close = () => {
    setOpen(false)
    window.requestAnimationFrame(() => triggerRef.current?.focus())
  }
  const toggle = () => {
    setOpen((current) => {
      if (!current) trackEvent('filters_opened', { surface: 'explorer' })
      return !current
    })
  }
  return (
    <>
      <div className="analysis-summary">
        <div>
          <span>Análise atual</span>
          <strong>{selected.measureLabel}: {selected.label}</strong>
          <small>{props.startYear}–{props.endYear} · {props.metric === 'count' ? 'Contagens' : 'Taxa por 100 mil'} · cidade, restante do RJ e Brasil</small>
        </div>
        <button ref={triggerRef} type="button" aria-expanded={open} onClick={toggle}><Filter size={18} />{open ? 'Fechar ajustes' : 'Ajustar análise'}</button>
      </div>
      <section className={`filter-rail${open ? ' filter-rail--open' : ''}`} aria-label="Filtros do explorador">
        <div className="filter-rail__mobile-heading">
          <strong>Ajustar análise</strong>
          <button type="button" aria-label="Fechar filtros" onClick={close}><X /></button>
        </div>
        <label>
          Tema
          <select value={props.theme} onChange={(event) => props.onTheme(event.target.value as Theme)}>
            <option value="respiratory">Respiratórias</option>
            <option value="cardiovascular">Cardiovasculares</option>
            <option value="cardiorespiratory">Cardiorrespiratórias</option>
            <option value="cancer">Câncer</option>
          </select>
        </label>
        <label className="filter-rail__indicator">
          Indicador
          <select value={props.indicatorId} onChange={(event) => props.onIndicator(event.target.value)}>
            {props.indicators.filter((item) => item.theme === props.theme).map((item) => (
              <option value={item.id} key={item.id}>{item.measureLabel}: {item.label}</option>
            ))}
          </select>
        </label>
        <label>
          Início
          <select value={props.startYear} onChange={(event) => props.onStartYear(Number(event.target.value))}>
            {years.filter((year) => year <= props.endYear).map((year) => <option key={year}>{year}</option>)}
          </select>
        </label>
        <label>
          Fim
          <select value={props.endYear} onChange={(event) => props.onEndYear(Number(event.target.value))}>
            {years.filter((year) => year >= props.startYear).map((year) => <option key={year}>{year}</option>)}
          </select>
        </label>
        <div className="metric-switch" role="group" aria-label="Medida exibida">
          <button type="button" className={props.metric === 'crude_rate_per_100k' ? 'is-selected' : ''} onClick={() => props.onMetric('crude_rate_per_100k')}>Taxa por 100 mil</button>
          <button type="button" className={props.metric === 'count' ? 'is-selected' : ''} onClick={() => props.onMetric('count')}>Contagens</button>
        </div>
        <div className="filter-actions">
          <button className="icon-action" type="button" onClick={() => { props.onDownload(); setFeedback('Recorte baixado em CSV.') }}><Download />Baixar recorte</button>
          <button className="icon-action" type="button" onClick={share}><Share2 />Compartilhar</button>
        </div>
        <span className="sr-only" aria-live="polite">{feedback}</span>
        <button className="filter-rail__apply" type="button" onClick={close}>Aplicar filtros</button>
      </section>
      {open ? <button className="filter-backdrop" aria-label="Fechar painel de filtros" onClick={close} /> : null}
    </>
  )
}
