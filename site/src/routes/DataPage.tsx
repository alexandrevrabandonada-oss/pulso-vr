import { Check, Download, FileJson, ShieldCheck } from 'lucide-react'
import { usePortal } from '../context/usePortal'

export function DataPage() {
  const { catalog, release } = usePortal()
  const generated = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(release.generatedAt))
  const releaseLabel = release.status === 'public_release_ready' ? 'Release aprovada — avisos permanecem visíveis' : 'Beta técnica — não liberada para publicação pública'
  return (
    <main className="content-page data-page">
      <header className="content-page__header"><p>Dados abertos</p><h1>Baixe o que o portal publica</h1><span>Os downloads obedecem às mesmas regras de supressão e proveniência da interface.</span></header>
      <section className="release-summary"><div><ShieldCheck /><span><strong>{release.releaseId}</strong>{releaseLabel}</span></div><dl><div><dt>Gerada em</dt><dd>{generated}</dd></div><div><dt>Indicadores</dt><dd>{catalog.indicators.length}</dd></div><div><dt>Artefatos</dt><dd>{release.artifacts.length}</dd></div></dl></section>
      {release.readiness ? <p className="release-readiness-line"><strong>Pré-voo:</strong> {release.readiness.blockerCount} bloqueios · {release.readiness.warningCount} avisos · mapa municipal com {release.readiness.mapValues} valores de saúde.</p> : null}
      <div className="download-list">
        <a href="/data/downloads/series-publicas.csv" download><Download /><span><strong>Séries públicas</strong>CSV em UTF-8, com taxas, contagens liberadas, intervalos e status.</span></a>
        <a href="/data/catalog.json" download><FileJson /><span><strong>Catálogo de indicadores</strong>Definições, unidades, fontes e cobertura em JSON.</span></a>
        <a href="/data/release.json" download><FileJson /><span><strong>Manifesto da release</strong>Hashes, cobertura, regras e estado das revisões.</span></a>
        <a href="/data/launch-readiness.json" download><ShieldCheck /><span><strong>Pré-voo de lançamento</strong>Bloqueios, avisos e próximos passos para a publicação pública.</span></a>
      </div>
      <section className="data-gap"><h2>Lacunas declaradas</h2><p>{release.coverage.missingDenominatorYears.length > 0 ? <>Não há denominador populacional municipal compatível para {release.coverage.missingDenominatorYears.join(', ')}. Esses períodos permanecem como lacunas: não são convertidos em zero nem interpolados.</> : 'Não há lacunas de denominador populacional na cobertura desta release.'}</p><p>O denominador de 2010 usa a população residente do Censo 2010; taxas e comparações só aparecem quando numerador, denominador e status temporal são compatíveis.</p></section>
      <section><h2>Portão de publicação</h2><ul className="gate-list">{Object.entries(release.publicationGate).map(([key, value]) => <li key={key}><Check />{key.replaceAll(/([A-Z])/g, ' $1')}: <strong>{value}</strong></li>)}</ul></section>
    </main>
  )
}
