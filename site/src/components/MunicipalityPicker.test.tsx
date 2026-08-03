import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MunicipalityPicker } from './MunicipalityPicker'

const municipalities = [
  { code: '3303302', name: 'Niterói', isVoltaRedonda: false },
  { code: '3304557', name: 'Rio de Janeiro', isVoltaRedonda: false },
  { code: '3306305', name: 'Volta Redonda', isVoltaRedonda: true },
]

describe('MunicipalityPicker', () => {
  it('finds a municipality without requiring accents', () => {
    const onSelect = vi.fn()
    render(<MunicipalityPicker municipalities={municipalities} selectedCode={null} onSelect={onSelect} />)
    fireEvent.change(screen.getByLabelText('Município do Rio de Janeiro'), { target: { value: 'niteroi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ver dados de Niterói' }))
    expect(onSelect).toHaveBeenCalledWith('3303302')
  })

  it('shows the selected municipality and does not force a default', () => {
    const { rerender } = render(<MunicipalityPicker municipalities={municipalities} selectedCode={null} onSelect={vi.fn()} />)
    expect(screen.getByLabelText('Município do Rio de Janeiro')).toHaveValue('')
    rerender(<MunicipalityPicker municipalities={municipalities} selectedCode="3304557" onSelect={vi.fn()} />)
    expect(screen.getByLabelText('Município do Rio de Janeiro')).toHaveValue('Rio de Janeiro')
  })
})
