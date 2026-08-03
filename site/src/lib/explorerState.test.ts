import { describe, expect, it } from 'vitest'
import type { Indicator } from '../types'
import { deriveExplorerState, explorerStateSearch } from './explorerState'

const indicators: Indicator[] = [
  {
    id: 'sih-resp-all', source: 'SIH', outcomeId: 'resp_all', label: 'Respiratórias', theme: 'respiratory',
    measure: 'hospitalization', measureLabel: 'Internações', definition: '', unit: 'AIHs', sourceLabel: 'SIH',
    cidRanges: ['J00-J99'], availableMetrics: ['crude_rate_per_100k', 'count'], geographyIds: [],
    yearStart: 2008, yearEnd: 2025, standardization: 'crude_only', mapStatus: 'context_only',
    allowsConclusion: '', doesNotAllowConclusion: '',
  },
  {
    id: 'sim-lung', source: 'SIM', outcomeId: 'lung', label: 'Pulmão', theme: 'cancer',
    measure: 'mortality', measureLabel: 'Mortalidade', definition: '', unit: 'Óbitos', sourceLabel: 'SIM',
    cidRanges: ['C33-C34'], availableMetrics: ['crude_rate_per_100k', 'count'], geographyIds: [],
    yearStart: 2011, yearEnd: 2024, standardization: 'crude_only', mapStatus: 'context_only',
    allowsConclusion: '', doesNotAllowConclusion: '',
  },
]

describe('deriveExplorerState', () => {
  it('selects the first indicator from a valid theme-only URL', () => {
    expect(deriveExplorerState('tema=cancer', indicators).indicator.id).toBe('sim-lung')
  })

  it('bounds years and normalizes an inverted period', () => {
    const state = deriveExplorerState('indicador=sim-lung&inicio=2099&fim=2000', indicators)
    expect([state.startYear, state.endYear]).toEqual([2011, 2024])
  })

  it('rejects unsupported measures and territories', () => {
    const state = deriveExplorerState('medida=incidencia&territorio=bairro', indicators)
    expect(state.metric).toBe('crude_rate_per_100k')
    expect(state.territory).toBe('all')
  })

  it('serializes a complete canonical URL state', () => {
    const query = explorerStateSearch(deriveExplorerState('tema=cancer', indicators))
    expect(query).toBe('tema=cancer&indicador=sim-lung&territorio=all&medida=crude_rate_per_100k&inicio=2011&fim=2024')
  })

  it('persists a valid municipality code without accepting arbitrary territory text', () => {
    const state = deriveExplorerState('indicador=sim-lung&municipio=3306305', indicators)
    expect(state.municipalityCode).toBe('3306305')
    expect(explorerStateSearch(state)).toContain('&municipio=3306305')
    expect(deriveExplorerState('municipio=volta-redonda', indicators).municipalityCode).toBeNull()
  })

  it('persists a valid map year and rejects malformed values', () => {
    const state = deriveExplorerState('indicador=sim-lung&ano_mapa=2022', indicators)
    expect(state.mapPeriod).toBe('2022')
    expect(explorerStateSearch(state)).toContain('&ano_mapa=2022')
    expect(deriveExplorerState('indicador=sim-lung&ano_mapa=ontem', indicators).mapPeriod).toBeNull()
  })
})
