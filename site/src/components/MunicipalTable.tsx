import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
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
  const [sort, setSort] = useState<'name' | 'rate'>('name')
  const [page, setPage] = useState(1)
  const pageSize = 15
  const period = values[0]?.period ?? 'período disponível'
  const valuesByCode = useMemo(() => new Map(values.map((value) => [value.geographyId, value])), [values])
  const rankByCode = useMemo(() => {
    const ranked = values
      .filter((value) => value.value !== null && !value.suppressed)
      .sort((left, right) => (right.value ?? -Infinity) - (left.value ?? -Infinity))
    let previousValue: number | null = null
    let previousRank = 0
    return new Map(ranked.map((value, index) => {
      const rank = previousValue === value.value ? previousRank : index + 1
      previousValue = value.value
      previousRank = rank
      return [value.geographyId, rank]
    }))
  }, [values])
  const visibleMunicipalities = useMemo(() => {
    const normalizedQuery = normalize(query.trim())
    const filtered = municipalities
      .filter((municipality) => !normalizedQuery || normalize(municipality.name).includes(normalizedQuery))
    return filtered.sort((left, right) => sort === 'rate'
      ? (valuesByCode.get(right.code)?.value ?? -Infinity) - (valuesByCode.get(left.code)?.value ?? -Infinity)
      : left.name.localeCompare(right.name, 'pt-BR'))
  }, [municipalities, query, sort, valuesByCode])
  useEffect(() => setPage(1), [query, sort, period])
  const pageCount = Math.max(1, Math.ceil(visibleMunicipalities.length / pageSize))
  const pageRows = visibleMunicipalities.slice((page - 1) * pageSize, page * pageSize)

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
        <label className="municipal-sort">Ordenar<select value={sort} onChange={(event) => setSort(event.target.value as 'name' | 'rate')}><option value="name">Nome</option><option value="rate">Maior taxa publicável</option></select></label>
      </div>
      <div className="municipal-table-wrap">
        <table className="municipal-table">
          <caption className="sr-only">Contagens e taxas municipais para {measureLabel} em {period}</caption>
          <thead><tr><th scope="col">Município</th><th scope="col">{measureLabel}</th><th scope="col">Taxa / 100 mil</th><th scope="col">Posição</th></tr></thead>
          <tbody>
            {pageRows.map((municipality) => {
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
      <nav className="municipal-pagination" aria-label="Paginação da tabela municipal"><button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Anterior</button><span>Página {page} de {pageCount} · {visibleMunicipalities.length} municípios encontrados</span><button type="button" disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>Próxima</button></nav>
      <p className="municipal-note">A posição considera {rankByCode.size} municípios com valor publicável neste período, preserva empates e não mede desempenho. “Não publicado” indica supressão ou ausência na fonte; não é zero.</p>
    </section>
  )
}
