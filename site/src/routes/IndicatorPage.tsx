import { AlertCircle, ArrowLeft, CheckCircle2, Database, ExternalLink } from 'lucide-react'
import { Link, useParams } from 'wouter'
import { usePortal } from '../context/usePortal'

export function IndicatorPage() {
  const { id } = useParams()
  const { catalog } = usePortal()
  const indicator = catalog.indicators.find((item) => item.id === id)
  if (!indicator) return <main className="content-page"><h1>Indicador não encontrado</h1><Link href="/explorador">Voltar ao explorador</Link></main>
  return (
    <main className="content-page indicator-page">
      <Link href={`/explorador?tema=${indicator.theme}&indicador=${indicator.id}`} className="back-link"><ArrowLeft />Voltar ao explorador</Link>
      <header className="content-page__header">
        <p>{indicator.measureLabel}</p>
        <h1>{indicator.label}</h1>
        <span>{indicator.sourceLabel} · {indicator.yearStart}–{indicator.yearEnd}</span>
      </header>
      <section className="definition-lead"><h2>Definição</h2><p>{indicator.definition}</p></section>
      <div className="conclusion-grid">
        <section><CheckCircle2 /><h2>O que permite concluir</h2><p>{indicator.allowsConclusion}</p></section>
        <section><AlertCircle /><h2>O que não permite concluir</h2><p>{indicator.doesNotAllowConclusion}</p></section>
      </div>
      <section className="method-table-section">
        <h2>Ficha do indicador</h2>
        <dl className="method-table">
          <div><dt>Unidade observada</dt><dd>{indicator.unit}</dd></div>
          <div><dt>Medidas disponíveis</dt><dd>Contagem e taxa bruta por 100 mil</dd></div>
          <div><dt>Território</dt><dd>Município de residência</dd></div>
          <div><dt>Comparador primário</dt><dd>RJ sem Volta Redonda</dd></div>
          <div><dt>Padronização</dt><dd>Taxa bruta; não equivale a taxa padronizada por idade</dd></div>
          <div><dt>CID-10</dt><dd>{indicator.cidRanges.join(', ') || 'Definição própria da fonte'}</dd></div>
        </dl>
      </section>
      <div className="content-actions"><Link href="/dados"><Database />Acessar dados públicos</Link><Link href="/metodos"><ExternalLink />Ler metodologia completa</Link></div>
    </main>
  )
}
