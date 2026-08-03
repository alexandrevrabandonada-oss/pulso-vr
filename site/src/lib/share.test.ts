import { describe, expect, it } from 'vitest'
import { buildCanonicalPath, buildSocialUrl } from './share'

describe('social sharing URLs', () => {
  it('builds deterministic encoded URLs without arbitrary copy', () => {
    const url = buildSocialUrl('https://pulsovr.online', { municipalityCode: '3304557', indicatorId: 'sim-alzheimer', period: '2022', template: 'answer', format: 'og', route: 'municipality' }, 'technical-beta')
    expect(url).toContain('/compartilhar?')
    expect(url).toContain('municipio=3304557')
    expect(url).not.toContain('titulo=')
  })
  it('restores profile and municipality destinations', () => {
    expect(buildCanonicalPath({ municipalityCode: '3304557', indicatorId: 'sim-lung', route: 'municipality' })).toBe('/municipios/3304557?indicador=sim-lung')
    expect(buildCanonicalPath({ municipalityCode: '3304557', indicatorId: 'sim-lung', period: '2022', route: 'profile' })).toBe('/perfis?indicador=sim-lung&municipio=3304557&periodo=2022')
  })
})
