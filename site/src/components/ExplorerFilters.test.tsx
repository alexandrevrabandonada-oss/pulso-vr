import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Indicator } from '../types'
import { ExplorerFilters } from './ExplorerFilters'

const indicator: Indicator = {
  id: 'sih-resp-all', source: 'SIH', outcomeId: 'resp_all', label: 'Todas as doenças respiratórias',
  theme: 'respiratory', measure: 'hospitalization', measureLabel: 'Internações hospitalares (AIHs)',
  definition: 'Eventos de internação.', unit: 'AIHs', sourceLabel: 'SIH/SUS', cidRanges: ['J00-J99'],
  availableMetrics: ['crude_rate_per_100k', 'count'], geographyIds: ['volta_redonda'], yearStart: 2008,
  yearEnd: 2025, standardization: 'crude_only', mapStatus: 'context_only', allowsConclusion: 'Descreve.',
  doesNotAllowConclusion: 'Não prova causa.',
}

describe('ExplorerFilters', () => {
  it('changes the metric through a real button control', () => {
    const onMetric = vi.fn()
    render(<ExplorerFilters theme="respiratory" indicators={[indicator]} indicatorId={indicator.id} territory="all" metric="crude_rate_per_100k" startYear={2008} endYear={2025} onTheme={vi.fn()} onIndicator={vi.fn()} onTerritory={vi.fn()} onMetric={onMetric} onStartYear={vi.fn()} onEndYear={vi.fn()} onDownload={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Contagens' }))
    expect(onMetric).toHaveBeenCalledWith('count')
  })

  it('exposes disabled age and sex controls honestly', () => {
    render(<ExplorerFilters theme="respiratory" indicators={[indicator]} indicatorId={indicator.id} territory="all" metric="crude_rate_per_100k" startYear={2008} endYear={2025} onTheme={vi.fn()} onIndicator={vi.fn()} onTerritory={vi.fn()} onMetric={vi.fn()} onStartYear={vi.fn()} onEndYear={vi.fn()} onDownload={vi.fn()} />)
    expect(screen.getByRole('combobox', { name: /Faixa etária/ })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Sexo' })).toBeDisabled()
  })

  it('changes the territory comparison through the public filter', () => {
    const onTerritory = vi.fn()
    render(<ExplorerFilters theme="respiratory" indicators={[indicator]} indicatorId={indicator.id} territory="all" metric="crude_rate_per_100k" startYear={2008} endYear={2025} onTheme={vi.fn()} onIndicator={vi.fn()} onTerritory={onTerritory} onMetric={vi.fn()} onStartYear={vi.fn()} onEndYear={vi.fn()} onDownload={vi.fn()} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Território' }), { target: { value: 'volta_redonda' } })
    expect(onTerritory).toHaveBeenCalledWith('volta_redonda')
  })

  it('downloads the visible cut through a button action', () => {
    const onDownload = vi.fn()
    render(<ExplorerFilters theme="respiratory" indicators={[indicator]} indicatorId={indicator.id} territory="all" metric="crude_rate_per_100k" startYear={2008} endYear={2025} onTheme={vi.fn()} onIndicator={vi.fn()} onTerritory={vi.fn()} onMetric={vi.fn()} onStartYear={vi.fn()} onEndYear={vi.fn()} onDownload={onDownload} />)
    fireEvent.click(screen.getByRole('button', { name: 'Baixar recorte' }))
    expect(onDownload).toHaveBeenCalledOnce()
    expect(screen.getByText('Recorte baixado em CSV.')).toBeInTheDocument()
  })
})
