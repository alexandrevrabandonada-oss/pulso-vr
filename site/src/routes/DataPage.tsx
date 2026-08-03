import { Check, Download, FileJson, ShieldCheck } from 'lucide-react'
import { usePortal } from '../context/PortalContext'

export function DataPage() {
  const { catalog, release } = usePortal()
  const generated = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(release.generatedAt))
  return (
    <main className="content-page data-page">
      <header className="content-page__header"><p>Dados abertos</p><h1>Baixe o que o portal publica</h1><span>Os downloads obedecem às mesmas regras de supressão e proveniência da interface.</span></header>
      <section className="release-summary"><div><ShieldCheck /><span><strong>{release.releaseId}</strong>Beta técnica — não liberada para publicação pública</span></div><dl><div><dt>Gerada em</dt><dd>{generated}</dd></div><div><dt>Indicadores</dt><dd>{catalog.indicators.length}</dd></div><div><dt>Artefatos</dt><dd>{release.artifacts.length}</dd></div></dl></section>
      <div className="download-list">
        <a href="/data/downloads/series-publicas.csv" download><Download /><span><strong>Séries públicas</strong>CSV em UTF-8, com taxas, contagens liberadas, intervalos e status.</span></a>
        <a href="/data/catalog.json" download><FileJson /><span><strong>Catálogo de indicadores</strong>Definições, unidades, fontes e cobertura em JSON.</span></a>
        <a href="/data/release.json" download><FileJson /><span><strong>Manifesto da release</strong>Hashes, cobertura, regras e estado das revisões.</span></a>
      </div>
      <section><h2>Portão de publicação</h2><ul className="gate-list">{Object.entries(release.publicationGate).map(([key, value]) => <li key={key}><Check />{key.replaceAll(/([A-Z])/g, ' $1')}: <strong>{value}</strong></li>)}</ul></section>
    </main>
  )
}
