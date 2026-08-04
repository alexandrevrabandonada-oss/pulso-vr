import { describe, expect, it } from 'vitest'
import { buildSeoMetadata, routeFromPath } from './seo'
import type { Indicator, Release } from '../types'

const release = { status: 'technical_beta_not_for_public_release' } as Release
const publicRelease = { status: 'public_release_ready' } as Release
const indicator = {
  id: 'sim-lung', label: 'Câncer de pulmão', source: 'SIM', sourceLabel: 'Sistema de Informação sobre Mortalidade',
  yearStart: 2010, yearEnd: 2024, measureLabel: 'Mortalidade', geographyBasis: 'residence', definition: 'Óbitos de residentes',
} as Indicator

describe('SEO metadata', () => {
  it('reconhece rotas públicas e rotas avançadas', () => {
    expect(routeFromPath('/')).toBe('home')
    expect(routeFromPath('/municipios/3304557')).toBe('municipality')
    expect(routeFromPath('/indicadores/sim-lung')).toBe('indicator')
    expect(routeFromPath('/explorador', '?indicador=sim-lung')).toBe('explorer')
    expect(routeFromPath('/nao-existe')).toBe('not-found')
  })

  it('bloqueia indexação durante a release beta', () => {
    const metadata = buildSeoMetadata({ origin: 'https://pulsovr.online', route: 'home', pathname: '/', release })
    expect(metadata.robots).toBe('noindex,nofollow')
    expect(metadata.title).toContain('92 municípios')
  })

  it('gera título, canonical e dados estruturados para indicador municipal público', () => {
    const metadata = buildSeoMetadata({ origin: 'https://pulsorj.online', route: 'municipality', pathname: '/municipios/3304557', municipalityCode: '3304557', municipalityName: 'Rio de Janeiro', indicator, release: publicRelease })
    expect(metadata.title).toContain('Câncer de pulmão em Rio de Janeiro')
    expect(metadata.canonicalUrl).toBe('https://pulsorj.online/municipios/3304557?indicador=sim-lung')
    expect(metadata.robots).toBe('index,follow')
    expect(metadata.structuredData.some((item) => item['@type'] === 'Dataset')).toBe(true)
  })

  it('não indexa o explorador técnico', () => {
    const metadata = buildSeoMetadata({ origin: 'https://pulsovr.online', route: 'explorer', pathname: '/explorador', release: publicRelease })
    expect(metadata.robots).toBe('noindex,follow')
  })
})
