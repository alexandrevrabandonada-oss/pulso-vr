import type { Release } from '../src/types'

export const config = { runtime: 'edge' }

async function loadRelease(origin: string) {
  const response = await fetch(new URL('/data/release.json', origin), { headers: { accept: 'application/json' } })
  if (!response.ok) throw new Error('release_unavailable')
  return response.json() as Promise<Release>
}

export default async function handler(request: Request) {
  const origin = new URL(request.url).origin
  try {
    const release = await loadRelease(origin)
    const publicRelease = release.status === 'public_release_ready' || release.readiness?.publicationAllowed === true
    const lines = ['User-agent: *']
    if (!publicRelease) lines.push('Disallow: /')
    else lines.push('Allow: /', 'Disallow: /api/', 'Disallow: /data/', 'Disallow: /compartilhar', 'Disallow: /explorador')
    if (publicRelease) lines.push(`Sitemap: ${origin}/sitemap.xml`)
    return new Response(lines.join('\n') + '\n', { headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600' } })
  } catch {
    return new Response('User-agent: *\nDisallow: /\n', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } })
  }
}
