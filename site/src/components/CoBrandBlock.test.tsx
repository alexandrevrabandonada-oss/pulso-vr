import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CoBrandBlock } from './CoBrandBlock'

describe('CoBrandBlock', () => {
  it('identifica a realização conjunta sem tratar a parceria como fonte', () => {
    render(<CoBrandBlock />)
    expect(screen.getByText('Realização conjunta')).toBeInTheDocument()
    expect(screen.getByAltText('VR Abandonada')).toBeInTheDocument()
    expect(screen.queryByText(/fonte epidemiológica/i)).not.toBeInTheDocument()
  })

  it('abre o Instagram oficial com isolamento da nova aba', () => {
    render(<CoBrandBlock />)
    const link = screen.getByRole('link', { name: /VR Abandonada no Instagram/i })
    expect(link).toHaveAttribute('href', 'https://www.instagram.com/vr_abandonada/')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('oferece uma variante de cabeçalho sem substituir a identidade do Observatório', () => {
    render(<CoBrandBlock variant="header" />)
    expect(screen.getByText('Projeto do Observatório')).toBeInTheDocument()
    expect(screen.getByText('VR Abandonada')).toBeInTheDocument()
  })
})
