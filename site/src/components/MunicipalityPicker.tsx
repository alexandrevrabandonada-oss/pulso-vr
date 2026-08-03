import { ArrowRight, MapPin, Search } from 'lucide-react'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { findMunicipality } from '../lib/municipalities'
import type { MapFeatureProperties } from '../types'

interface MunicipalityPickerProps {
  municipalities: MapFeatureProperties[]
  selectedCode: string | null
  onSelect: (code: string) => void
}

export function MunicipalityPicker({ municipalities, selectedCode, onSelect }: MunicipalityPickerProps) {
  const sorted = useMemo(
    () => [...municipalities].sort((left, right) => left.name.localeCompare(right.name, 'pt-BR')),
    [municipalities],
  )
  const selected = sorted.find((item) => item.code === selectedCode) ?? null
  const [query, setQuery] = useState(selected?.name ?? '')
  const match = useMemo(() => {
    return findMunicipality(query, sorted)
  }, [query, sorted])

  useEffect(() => setQuery(selected?.name ?? ''), [selected?.name])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (match) onSelect(match.code)
  }

  return (
    <section className="municipality-picker" aria-labelledby="municipality-picker-title">
      <div>
        <span>1 · Escolha a cidade</span>
        <h2 id="municipality-picker-title">Qual cidade você quer conhecer?</h2>
        <p>Digite o nome ou escolha no mapa. Há dados publicados para os 92 municípios do estado.</p>
      </div>
      <form onSubmit={submit} className="municipality-search" role="search">
        <label htmlFor="municipality-input">Município do Rio de Janeiro</label>
        <div className="municipality-search__control">
          <MapPin aria-hidden="true" />
          <input
            id="municipality-input"
            list="municipality-options"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Digite uma cidade, por exemplo Niterói"
            autoComplete="off"
          />
          <button type="submit" disabled={!match} aria-label={match ? `Ver dados de ${match.name}` : 'Digite o nome de uma cidade'}>
            <span>Ver dados</span><ArrowRight aria-hidden="true" />
          </button>
        </div>
        <datalist id="municipality-options">
          {sorted.map((municipality) => <option value={municipality.name} key={municipality.code} />)}
        </datalist>
        <small>{match ? `Abrir o painel de ${match.name}` : <><Search aria-hidden="true" /> Busque entre 92 cidades</>}</small>
      </form>
    </section>
  )
}
