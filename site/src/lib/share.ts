import type { ShareContext, ShareFormat, ShareRoute, ShareTemplate } from '../types'

export const SHARE_TEMPLATES: Array<{ id: ShareTemplate; label: string; description: string }> = [
  { id: 'answer', label: 'Resposta', description: 'Valor, período e comparação.' },
  { id: 'evolution', label: 'Evolução', description: 'Série temporal sem interpolar lacunas.' },
  { id: 'map', label: 'Mapa', description: 'Contexto estadual e cidade destacada.' },
]
export const SHARE_FORMATS: Array<{ id: ShareFormat; label: string; size: string }> = [
  { id: 'og', label: 'Link e preview', size: '1200 × 630' },
  { id: 'feed', label: 'Feed', size: '1080 × 1350' },
  { id: 'story', label: 'Stories', size: '1080 × 1920' },
]

function clean(value?: string) { return value?.trim() || undefined }

export function shareParameters(context: ShareContext, releaseId: string) {
  const params = new URLSearchParams({ modelo: context.template, formato: context.format, release: releaseId })
  const values: Array<[string, string | undefined]> = [
    ['municipio', clean(context.municipalityCode)], ['indicador', clean(context.indicatorId)],
    ['periodo', clean(context.period)], ['metrica', clean(context.metricKind)], ['rota', clean(context.route)],
  ]
  values.forEach(([key, value]) => { if (value) params.set(key, value) })
  return params
}

export function buildSocialUrl(origin: string, context: ShareContext, releaseId: string) {
  return `${origin}/compartilhar?${shareParameters(context, releaseId)}`
}

export function buildCardUrl(origin: string, context: ShareContext, releaseId: string) {
  return `${origin}/api/share-card?${shareParameters(context, releaseId)}`
}

export function buildCanonicalPath(context: Pick<ShareContext, 'municipalityCode' | 'indicatorId' | 'period' | 'route'>) {
  const route: ShareRoute = context.route ?? (context.municipalityCode ? 'municipality' : 'indicator')
  const query = new URLSearchParams()
  if (context.indicatorId) query.set('indicador', context.indicatorId)
  if (context.municipalityCode) query.set('municipio', context.municipalityCode)
  if (context.period) query.set('periodo', context.period)
  if (route === 'municipality' && context.municipalityCode) return `/municipios/${context.municipalityCode}${context.indicatorId ? `?indicador=${encodeURIComponent(context.indicatorId)}` : ''}`
  if (route === 'profile') return `/perfis?${query}`
  if (route === 'explorer') return `/explorador?${query}`
  return context.indicatorId ? `/indicadores/${encodeURIComponent(context.indicatorId)}` : '/'
}
