import { AlertTriangle, Info } from 'lucide-react'

export function StatusNotice({ provisional, source }: { provisional: boolean; source: 'SIH' | 'SIM' | 'SIA' }) {
  return (
    <div className="status-notices">
      {provisional ? (
        <div className="status-notice status-notice--warning">
          <AlertTriangle aria-hidden="true" />
          <div><strong>Dados provisórios</strong><span>Valores podem mudar em atualizações da fonte.</span></div>
        </div>
      ) : null}
      <div className="status-notice">
        <Info aria-hidden="true" />
        {source === 'SIH' ? (
          <div><strong>Internações são eventos/AIHs, não pessoas únicas</strong><span>Uma pessoa pode ter mais de uma internação.</span></div>
        ) : source === 'SIA' ? (
          <div><strong>Produção ambulatorial é do estabelecimento</strong><span>Não representa residência, risco, prevalência ou incidência municipal.</span></div>
        ) : (
          <div><strong>Óbitos não representam incidência</strong><span>Mortalidade por câncer não mede casos novos na população.</span></div>
        )}
      </div>
    </div>
  )
}
