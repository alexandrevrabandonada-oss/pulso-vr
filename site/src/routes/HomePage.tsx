import { ArrowRight, ChartNoAxesCombined, Download, FileSearch, Map, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'wouter'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { loadSeries } from '../lib/data'
import type { Observation } from '../types'
import { usePortal } from '../context/usePortal'

export function HomePage() {
  const { catalog, topology } = usePortal()
  const indicator = catalog.indicators.find((item) => item.id === 'sih-resp-all') ?? catalog.indicators[0]
  const [observations, setObservations] = useState<Observation[]>([])
  useEffect(() => {
    loadSeries(indicator.id).then((payload) => setObservations(payload.observations))
  }, [indicator.id])
  return (
    <main>
      <section className="home-hero">
        <div className="home-hero__copy">
          <h1>Saúde em Volta Redonda, vista no território e no tempo</h1>
          <p>Explore dados de doenças respiratórias, cardiovasculares e cardiorrespiratórias, compare Volta Redonda com o restante do Rio de Janeiro e acompanhe o comparador nacional conforme cada série é validada.</p>
          <Link href="/explorador" className="primary-button">Explorar os dados <ArrowRight /></Link>
          <p className="hero-method-note">Informação pública, por residência e com limitações visíveis.</p>
        </div>
        <div className="home-hero__data" aria-label="Prévia do explorador de dados">
          <TerritoryMap topology={topology} compact />
          {observations.length ? (
            <TimeSeriesChart
              compact
              indicator={indicator}
              observations={observations}
              metric="crude_rate_per_100k"
              geographyLabels={catalog.geographies}
              startYear={2018}
            />
          ) : null}
        </div>
        <div className="river-rule" aria-hidden="true">
          <svg viewBox="0 0 800 72" preserveAspectRatio="none"><path d="M0 38C90 5 130 66 220 34S350 57 430 31 560 55 640 30 720 52 800 22" /><path d="M0 51C90 18 130 79 220 47S350 70 430 44 560 68 640 43 720 65 800 35" /></svg>
        </div>
      </section>

      <section className="lenses-section">
        <h2>Três lentes para entender os dados</h2>
        <div className="lenses-row">
          <article><Map /><div><h3>Território</h3><p>Compare Volta Redonda com o RJ sem o município e, quando validado, com o Brasil.</p><Link href="/explorador">Abrir mapa <ArrowRight /></Link></div></article>
          <article><ChartNoAxesCombined /><div><h3>Tempo</h3><p>Observe tendências, lacunas e marcos que mudam a interpretação das séries.</p><Link href="/explorador">Ver séries <ArrowRight /></Link></div></article>
          <article><Users /><div><h3>População</h3><p>Leia diferenças por idade e sexo sem confundir contagens com taxas comparáveis.</p><Link href="/perfis">Explorar perfis <ArrowRight /></Link></div></article>
        </div>
      </section>

      <section className="evidence-band">
        <div><h2>Informação confiável, método transparente</h2><p>Todo número publicado liga fonte, unidade, período, território e status do dado.</p></div>
        <div className="evidence-band__items">
          <Link href="/metodos"><FileSearch /><span><strong>Como ler estes dados</strong>Definições, rupturas e limites</span></Link>
          <Link href="/dados"><Download /><span><strong>Dados e proveniência</strong>Arquivos públicos e manifestos</span></Link>
        </div>
      </section>
    </main>
  )
}
