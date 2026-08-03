import { Instagram } from 'lucide-react'
import { BrandMark } from './BrandMark'

const INSTAGRAM_URL = 'https://www.instagram.com/vr_abandonada/'
export type CoBrandVariant = 'default' | 'header' | 'page'

export function CoBrandBlock({ compact = false, variant = 'default' }: { compact?: boolean; variant?: CoBrandVariant }) {
  return (
    <section className={`co-brand co-brand--${variant}${compact ? ' co-brand--compact' : ''}`} aria-label="Realização conjunta entre o Observatório e VR Abandonada">
      <span className="co-brand__label">Realização conjunta</span>
      <div className="co-brand__marks">
        {variant === 'header' ? <span className="co-brand__project">Projeto do Observatório</span> : <BrandMark compact />}
        <span className="co-brand__divider" aria-hidden="true" />
        <a
          className="co-brand__partner"
          href={INSTAGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="VR Abandonada no Instagram, abre em nova aba"
        >
          <img src="/brand/vr-abandonada.webp" alt="VR Abandonada" width="72" height="72" />
          <span><Instagram aria-hidden="true" />{variant === 'header' ? 'VR Abandonada' : '@vr_abandonada'}</span>
        </a>
      </div>
      {variant === 'page' ? <p className="co-brand__note">A parceria é institucional. As fontes, definições e limitações epidemiológicas estão identificadas em cada dado.</p> : null}
    </section>
  )
}
