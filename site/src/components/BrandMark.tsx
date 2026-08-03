export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand" aria-label="Observatório Saúde & Ambiente — Volta Redonda">
      <svg className="brand__mark" viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r="19" fill="none" stroke="currentColor" strokeWidth="8" />
        <circle cx="32" cy="32" r="6" fill="#e3530f" />
        <path d="M32 1 37 21 32 18 27 21ZM63 32 43 37 46 32 43 27ZM32 63 27 43 32 46 37 43ZM1 32 21 27 18 32 21 37Z" fill="currentColor" />
      </svg>
      <span className="brand__text">
        <span className="brand__name">Observatório</span>
        {compact ? null : <span className="brand__descriptor">Saúde &amp; Ambiente — Volta Redonda</span>}
      </span>
    </span>
  )
}
