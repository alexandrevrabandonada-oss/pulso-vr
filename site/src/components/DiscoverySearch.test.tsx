import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DiscoverySearch } from './DiscoverySearch'
import type { Indicator } from '../types'

const municipalities = [
  { code: '3304557', name: 'Rio de Janeiro', isVoltaRedonda: false },
  { code: '3306305', name: 'Volta Redonda', isVoltaRedonda: true },
]

const indicators = [{
  id: 'sim-lung', source: 'SIM', outcomeId: 'lung', label: 'Traqueia, brônquios e pulmão',
  theme: 'cancer', measure: 'mortality', measureLabel: 'Mortalidade', definition: '', unit: '',
  sourceLabel: 'SIM', cidRanges: ['C33-C34'], availableMetrics: ['crude_rate_per_100k'], geographyIds: [],
  yearStart: 2022, yearEnd: 2024, standardization: 'crude_only', mapStatus: 'validated',
  allowsConclusion: '', doesNotAllowConclusion: '', synonyms: ['câncer de pulmão', 'pulmão'],
}] satisfies Indicator[]

describe('DiscoverySearch', () => {
  it('encontra cidade sem acento e indicador por termo popular', () => {
    const onOpen = vi.fn()
    render(<DiscoverySearch municipalities={municipalities} indicators={indicators} onOpen={onOpen} />)
    fireEvent.change(screen.getByLabelText('Qual cidade?'), { target: { value: 'rio de janeiro' } })
    fireEvent.change(screen.getByLabelText('Qual assunto?'), { target: { value: 'pulmao' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ver dados' }))
    expect(onOpen).toHaveBeenCalledWith('3304557', 'sim-lung')
  })
})
