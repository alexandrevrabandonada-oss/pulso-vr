import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { formatMetric } from '../lib/format'
import type { MapFeatureProperties, MapValue } from '../types'

interface MunicipalTableProps {
  municipalities: MapFeatureProperties[]
  values: MapValue[]
  measureLabel: string
  selectedCode: string | null
  onSelect: (code: string) => void
}

function normalize(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

export function MunicipalTable({ municipalities, values, measureLabel, selectedCode, onSelect }: MunicipalTableProps) {
  const [query, setQuery] = useState('')
  const valuesByCode = useMemo(() => new Map(values.map((value) => [value.geographyId, value])), [values])
  const rankByCode = useMemo(() => {
    const ranked = values
      .filter((value) => value.value !== null && !value.suppressed)
      .sort((left, right) => (right.value ?? -Infinity) - (left.value ?? -Infinity))
    return new Map(ranked.map((value, index) => [value.geographyId, index + 1]))
  }, [values])
  const visibleMunicipalities = useMemo(() => {
    const normalizedQuery = normalize(query.trim())
    return municipalities
      .filter((municipality) => !normalizedQuery || normalize(municipality.name).includes(normalizedQuery))
      .sort((left, right) => left.name.localeCompare(right.name, 'pt-BR'))
  }, [municipalities, query])
  const period = values[0]?.period ?? 'período disponível'

  return (
    <section className="municipal-section" aria-labelledby="municipal-title">
      <div className="municipal-section__heading">
        <div>
          <p className="eyebrow">Visão estadual</p>
          <h2 id="municipal-title">Dados por município</h2>
          <p>{measureLabel} · {period} · {municipalities.length} municípios na malha do RJ</p>
        </div>
        <label className="municipal-search">
          <Search aria-hidden="true" />
          <span className="sr-only">Buscar município</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar cidade" />
        </label>
      </div>
      <div className="municipal-table-wrap">
        <table className="municipal-table">
          <caption className="sr-only">Contagens e taxas municipais para {measureLabel} em {period}</caption>
          <thead><tr><th scope="col">Município</th><th scope="col">{measureLabel}</th><th scope="col">Taxa / 100 mil</th><th scope="col">Posição</th></tr></thead>
          <tbody>
            {visibleMunicipalities.map((municipality) => {
              const value = valuesByCode.get(municipality.code)
              const suppressed = value?.suppressed || (value && value.count === null && value.value === null)
              return (
                <tr key={municipality.code} className={selectedCode === municipality.code ? 'is-selected' : undefined}>
                  <th scope="row"><button type="button" onClick={() => onSelect(municipality.code)}>{municipality.name}</button></th>
                  <td>{suppressed ? 'Não publicado' : formatMetric(value?.count ?? null, 'count')}</td>
                  <td>{suppressed ? 'Não publicado' : formatMetric(value?.value ?? null, 'crude_rate_per_100k')}</td>
                  <td>{suppressed ? '—' : rankByCode.get(municipality.code) ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!visibleMunicipalities.length ? <p className="municipal-empty">Nenhum município corresponde à busca.</p> : null}
      </div>
      <p className="municipal-note">A posição é descritiva entre valores publicáveis e não mede desempenho. “Não publicado” indica supressão ou ausência na fonte; não é zero.</p>
    </section>
  )
}
