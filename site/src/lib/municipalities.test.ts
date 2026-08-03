import { describe, expect, it } from 'vitest'
import { findMunicipality, municipalProperties } from './municipalities'

const municipalities = [
  { code: '3303302', name: 'Niterói', isVoltaRedonda: false },
  { code: '3304557', name: 'Rio de Janeiro', isVoltaRedonda: false },
]

describe('municipality helpers', () => {
  it('finds names without accents and by prefix', () => {
    expect(findMunicipality('niteroi', municipalities)?.code).toBe('3303302')
    expect(findMunicipality('rio de jan', municipalities)?.code).toBe('3304557')
  })

  it('reads municipalities from the topology', () => {
    expect(municipalProperties({ objects: { municipalities: { geometries: [{ properties: municipalities[0] }] } } })).toEqual([municipalities[0]])
  })
})
