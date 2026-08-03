import { resolveShareModel, safeValue } from './share-data'

export const config = { runtime: 'edge' }
const escape = (value: string) => value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)

export default async function handler(request: Request) {
  try {
    const url = new URL(request.url); const model = await resolveShareModel(url)
    if (!model) return new Response('Parâmetros inválidos.', { status: 400, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } })
    const title = `${model.indicator.label}${model.municipalityName ? ` em ${model.municipalityName}` : ''} | Observatório Estadual de Saúde do RJ`
    const description = model.item?.suppressionStatus === 'published' ? `${safeValue(model)}. ${model.item.period ?? ''}. Consulte fonte, comparação e limitações.` : 'Dado protegido ou indisponível. Consulte a explicação e a cobertura no Observatório.'
    const image = new URL(`/api/share-card?${url.searchParams}`, url.origin).toString()
    const html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escape(title)}</title><meta name="description" content="${escape(description)}"><meta name="robots" content="noindex,follow"><meta property="og:type" content="website"><meta property="og:site_name" content="Observatório Estadual de Saúde do RJ"><meta property="og:locale" content="pt_BR"><meta property="og:title" content="${escape(title)}"><meta property="og:description" content="${escape(description)}"><meta property="og:image" content="${escape(image)}"><meta property="og:image:alt" content="Card público do Observatório Estadual de Saúde do RJ e VR Abandonada"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="${escape(model.canonicalUrl)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${escape(title)}"><meta name="twitter:description" content="${escape(description)}"><meta name="twitter:image" content="${escape(image)}"><link rel="canonical" href="${escape(model.canonicalUrl)}"></head><body><main><h1>${escape(title)}</h1><p>${escape(description)}</p><p><a href="${escape(model.canonicalUrl)}">Abrir dado no Observatório</a></p></main><script>setTimeout(function(){location.replace(${JSON.stringify(model.canonicalUrl)})},600)</script><noscript><a href="${escape(model.canonicalUrl)}">Continuar para o Observatório</a></noscript></body></html>`
    return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400' } })
  } catch { return new Response('Preview temporariamente indisponível.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } }) }
}
