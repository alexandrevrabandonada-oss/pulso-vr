import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Indicator } from '../types'
import { IndicatorFinder } from './IndicatorFinder'

const lungIndicator: Indicator = {
  id: 'sim-lung', source: 'SIM', outcomeId: 'lung', label: 'Traqueia, brônquios e pulmão',
  theme: 'cancer', measure: 'mortality', measureLabel: 'Mortalidade', definition: 'Óbitos.',
  unit: 'óbitos', sourceLabel: 'SIM — Ministério da Saúde', cidRanges: ['C33-C34'],
  availableMetrics: ['crude_rate_per_100k', 'count'], geographyIds: ['volta_redonda'], yearStart: 2010,
  yearEnd: 2024, standardization: 'crude_only', mapStatus: 'validated', allowsConclusion: 'Descreve.',
  municipalPeriods: ['2022'],
  doesNotAllowConclusion: 'Não prova causa.',
}

describe('IndicatorFinder', () => {
  it('finds indicators without requiring accents and selects the result', () => {
    const onSelect = vi.fn()
    render(<IndicatorFinder indicators={[lungIndicator]} onSelect={onSelect} />)

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar doença ou indicador' }), {
      target: { value: 'pulmao' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Traqueia, brônquios e pulmão/ }))

    expect(onSelect).toHaveBeenCalledWith('sim-lung')
    expect(screen.getByText(/Mapa municipal · 2022/)).toBeInTheDocument()
  })
})
