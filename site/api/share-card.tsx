import React from 'react'
import { ImageResponse } from '@vercel/og'
import { cardSize, lineSegments, metricName, resolveShareModel, safeValue } from './share-data'

export const config = { runtime: 'edge' }

const base: React.CSSProperties = { display: 'flex', boxSizing: 'border-box', fontFamily: 'sans-serif' }

export default async function handler(request: Request) {
  try {
    const model = await resolveShareModel(new URL(request.url))
    if (!model) return new Response('Parâmetros inválidos.', { status: 400, headers: { 'Cache-Control': 'no-store' } })
    const size = cardSize(model.format); const protectedValue = !model.item || model.item.suppressionStatus !== 'published'
    const title = model.municipalityName ? `${model.indicator.label} em ${model.municipalityName}` : model.indicator.label
    const segments = lineSegments(model.values)
    const logoUrl = new URL('/brand/vr-abandonada.webp', new URL(request.url).origin).toString()
    const content = <div style={{ ...base, width: '100%', height: '100%', flexDirection: 'column', justifyContent: 'space-between', padding: model.format === 'og' ? 54 : 72, color: '#0b0b0b', background: '#fff8df' }}>
      <div style={{ ...base, justifyContent: 'space-between', alignItems: 'center' }}><div style={{ ...base, alignItems: 'center', gap: 16 }}><div style={{ ...base, width: 48, height: 48, borderRadius: 24, background: '#ffd900', border: '5px solid #0b0b0b' }} /><b style={{ fontSize: 24 }}>OBSERVATÓRIO ESTADUAL DE SAÚDE DO RJ</b></div><div style={{ ...base, alignItems: 'center', gap: 12 }}><img src={logoUrl} width="54" height="54" style={{ borderRadius: 12, objectFit: 'cover' }} /><span style={{ fontSize: 20, padding: '10px 18px', border: '3px solid #0b0b0b', borderRadius: 99 }}>Dados públicos</span></div></div>
      <div style={{ ...base, flexDirection: 'column', gap: 18 }}><span style={{ fontSize: 24, textTransform: 'uppercase', letterSpacing: 2 }}>{model.template === 'answer' ? 'Resposta municipal' : model.template === 'evolution' ? 'Evolução temporal' : 'Contexto estadual'}</span><h1 style={{ margin: 0, maxWidth: 900, fontSize: model.format === 'og' ? 55 : 66, lineHeight: 1.02 }}>{title}</h1><p style={{ margin: 0, fontSize: 25 }}>{metricName(model.metricKind ?? model.item?.metricKind ?? undefined)} · {model.period ?? model.item?.period ?? 'período disponível'} · {model.indicator.sourceLabel}</p></div>
      {model.template === 'evolution' ? <div style={{ ...base, height: 230, padding: 24, background: '#fff', border: '4px solid #0b0b0b', borderRadius: 28 }}><svg width="100%" height="100%" viewBox="0 0 760 180">{segments.map((path, index) => <path key={index} d={path} fill="none" stroke="#0b0b0b" strokeWidth="8" strokeLinecap="round" />)}</svg></div> : model.template === 'map' ? <div style={{ ...base, alignItems: 'center', gap: 30, padding: 30, background: '#ffd900', border: '4px solid #0b0b0b', borderRadius: 34 }}><div style={{ ...base, width: 180, height: 140, borderRadius: '55% 45% 62% 38%', background: '#fff', border: '5px solid #0b0b0b', alignItems: 'center', justifyContent: 'center', fontSize: 54 }}>RJ</div><div style={{ ...base, flexDirection: 'column' }}><b style={{ fontSize: 28 }}>Município destacado</b><span style={{ fontSize: 44 }}>{model.municipalityName ?? 'Visão estadual'}</span><strong style={{ fontSize: 54 }}>{safeValue(model)}</strong></div></div> : <div style={{ ...base, alignItems: 'flex-end', justifyContent: 'space-between', gap: 26 }}><div style={{ ...base, alignItems: 'flex-end', gap: 18 }}><strong style={{ fontSize: protectedValue ? 54 : 96 }}>{safeValue(model)}</strong>{!protectedValue ? <span style={{ fontSize: 25, paddingBottom: 16 }}>por 100 mil</span> : null}</div>{model.item?.comparisonAvailable && model.item.restOfStateValue !== null ? <div style={{ ...base, flexDirection: 'column', padding: 20, borderLeft: '4px solid #0b0b0b' }}><span style={{ fontSize: 20 }}>RJ sem o município</span><b style={{ fontSize: 38 }}>{new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(model.item.restOfStateValue)}</b></div> : null}</div>}
      <div style={{ ...base, justifyContent: 'space-between', borderTop: '4px solid #0b0b0b', paddingTop: 20, fontSize: 18 }}><span>{model.indicator.source} · {model.indicator.geographyBasis === 'establishment' ? 'estabelecimento' : 'residência'} · {model.item?.dataStatus ?? model.release.status}</span><span>Realização conjunta · Observatório + VR Abandonada</span></div>
    </div>
    return new ImageResponse(content, { ...size, headers: { 'Cache-Control': 'public, s-maxage=31536000, stale-while-revalidate=86400' } })
  } catch { return new Response('Não foi possível gerar o card.', { status: 503, headers: { 'Cache-Control': 'no-store' } }) }
}
