import { ArrowRight, MapPin, Search } from 'lucide-react'
import { FormEvent, useDeferredValue, useMemo, useState } from 'react'
import { normalizeMunicipalityName } from '../lib/municipalities'
import { trackEvent } from '../lib/analytics'
import type { Indicator, MapFeatureProperties } from '../types'

interface DiscoverySearchProps {
  municipalities: MapFeatureProperties[]
  indicators: Indicator[]
  initialMunicipalityCode?: string | null
  onOpen: (municipalityCode: string, indicatorId: string) => void
  compact?: boolean
}

const POPULAR = ['sih-pneumonia', 'sim-lung', 'sim-all-malignant-neoplasms', 'sim-acute-myocardial-infarction']

function normalizedIndicatorText(indicator: Indicator) {
  return normalizeMunicipalityName([
    indicator.label, indicator.measureLabel, indicator.sourceLabel, indicator.theme,
    ...(indicator.synonyms ?? []),
  ].join(' '))
}

export function DiscoverySearch({ municipalities, indicators, initialMunicipalityCode = null, onOpen, compact = false }: DiscoverySearchProps) {
  const initialMunicipality = municipalities.find((item) => item.code === initialMunicipalityCode)
  const [cityQuery, setCityQuery] = useState(initialMunicipality?.name ?? '')
  const [indicatorQuery, setIndicatorQuery] = useState('')
  const deferredIndicatorQuery = useDeferredValue(indicatorQuery)
  const cityTerm = normalizeMunicipalityName(cityQuery)
  const municipality = useMemo(() => municipalities.find((item) => normalizeMunicipalityName(item.name) === cityTerm)
    ?? municipalities.find((item) => normalizeMunicipalityName(item.name).startsWith(cityTerm)), [cityTerm, municipalities])
  const indicatorMatches = useMemo(() => {
    const term = normalizeMunicipalityName(deferredIndicatorQuery)
    if (!term) return POPULAR.map((id) => indicators.find((item) => item.id === id)).filter((item): item is Indicator => Boolean(item))
    return indicators.filter((item) => normalizedIndicatorText(item).includes(term)).slice(0, 6)
  }, [deferredIndicatorQuery, indicators])
  const selectedIndicator = indicatorMatches[0] ?? null

  const open = (event: FormEvent) => {
    event.preventDefault()
    if (!municipality || !selectedIndicator) return
    trackEvent('discovery_search', { hasMunicipality: true, indicatorId: selectedIndicator.id })
    onOpen(municipality.code, selectedIndicator.id)
  }

  return (
    <form className={`discovery-search${compact ? ' discovery-search--compact' : ''}`} onSubmit={open} role="search" aria-label="Buscar cidade e assunto de saúde">
      <div className="discovery-field">
        <label htmlFor="discovery-city">Qual cidade?</label>
        <div><MapPin aria-hidden="true" /><input id="discovery-city" list="discovery-cities" value={cityQuery} onChange={(event) => setCityQuery(event.target.value)} placeholder="Digite o município" autoComplete="off" /></div>
        <datalist id="discovery-cities">{municipalities.map((item) => <option key={item.code} value={item.name} />)}</datalist>
      </div>
      <div className="discovery-field">
        <label htmlFor="discovery-indicator">Qual assunto?</label>
        <div><Search aria-hidden="true" /><input id="discovery-indicator" value={indicatorQuery} onChange={(event) => setIndicatorQuery(event.target.value)} placeholder="Ex.: pneumonia, pulmão, infarto" autoComplete="off" /></div>
        <div className="discovery-suggestions" aria-label="Indicadores sugeridos">
          {indicatorMatches.slice(0, 4).map((item) => <button type="button" key={item.id} aria-pressed={selectedIndicator?.id === item.id} onClick={() => setIndicatorQuery(item.label)}>{item.label}</button>)}
        </div>
      </div>
      <button className="discovery-submit" type="submit" disabled={!municipality || !selectedIndicator}>Ver dados <ArrowRight /></button>
    </form>
  )
}
