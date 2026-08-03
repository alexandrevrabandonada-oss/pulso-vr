import { describe, expect, it } from 'vitest'
import { lineSegments, parseShareRequest } from '../../api/share-data'

describe('safe social card contracts', () => {
  it('rejects arbitrary indicators and text-like periods', () => {
    expect(parseShareRequest(new URL('https://example.test/compartilhar?indicador=%3Cscript%3E&modelo=answer&formato=og'))).toBeNull()
    expect(parseShareRequest(new URL('https://example.test/compartilhar?indicador=sim-lung&modelo=answer&formato=og&periodo=2022%20texto'))).toBeNull()
    expect(parseShareRequest(new URL('https://example.test/compartilhar?indicador=sim-lung&modelo=answer&formato=og&release=%3Cmeta%3E'))).toBeNull()
  })
  it('breaks sparse series instead of crossing a missing year', () => {
    const paths = lineSegments([{ period: '2022', value: 2 }, { period: '2023', value: null }, { period: '2024', value: 4 }])
    expect(paths).toHaveLength(2)
  })
})
