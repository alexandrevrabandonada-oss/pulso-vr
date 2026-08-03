import { Instagram } from 'lucide-react'
import { BrandMark } from './BrandMark'

const INSTAGRAM_URL = 'https://www.instagram.com/vr_abandonada/'

export function CoBrandBlock({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`co-brand${compact ? ' co-brand--compact' : ''}`} aria-label="Realização conjunta">
      <span className="co-brand__label">Realização conjunta</span>
      <div className="co-brand__marks">
        <BrandMark compact />
        <span className="co-brand__divider" aria-hidden="true" />
        <a
          className="co-brand__partner"
          href={INSTAGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="VR Abandonada no Instagram, abre em nova aba"
        >
          <img src="/brand/vr-abandonada.webp" alt="VR Abandonada" width="72" height="72" />
          <span><Instagram aria-hidden="true" />@vr_abandonada</span>
        </a>
      </div>
    </section>
  )
}
