import { ArrowRight, ChartNoAxesCombined, Download, FileSearch, Map, MapPin, Users } from 'lucide-react'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'wouter'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { loadSeries } from '../lib/data'
import { findMunicipality, municipalProperties } from '../lib/municipalities'
import type { Observation } from '../types'
import { usePortal } from '../context/usePortal'

export function HomePage() {
  const { catalog, topology } = usePortal()
  const [, navigate] = useLocation()
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const [cityQuery, setCityQuery] = useState('')
  const cityMatch = useMemo(() => findMunicipality(cityQuery, municipalities), [cityQuery, municipalities])
  const indicator = catalog.indicators.find((item) => item.id === 'sih-resp-all') ?? catalog.indicators[0]
  const [observations, setObservations] = useState<Observation[]>([])
  useEffect(() => {
    loadSeries(indicator.id).then((payload) => setObservations(payload.observations))
  }, [indicator.id])
  const openCity = (event: FormEvent) => {
    event.preventDefault()
    if (cityMatch) navigate(`/explorador?municipio=${cityMatch.code}`)
  }
  return (
    <main>
      <section className="home-hero">
        <div className="home-hero__copy">
          <p className="hero-eyebrow">Observatório estadual de saúde</p>
          <h1>Doenças no Rio de Janeiro, cidade por cidade</h1>
          <p>Escolha qualquer uma das 92 cidades, consulte internações e óbitos por residência e compare sua taxa com o restante do estado e com o Brasil.</p>
          <form className="home-city-search" onSubmit={openCity} role="search">
            <label htmlFor="home-city-input">Comece pela sua cidade</label>
            <div>
              <MapPin aria-hidden="true" />
              <input id="home-city-input" list="home-city-options" value={cityQuery} onChange={(event) => setCityQuery(event.target.value)} placeholder="Digite o município" autoComplete="off" />
              <button type="submit" disabled={!cityMatch} aria-label={cityMatch ? `Abrir dados de ${cityMatch.name}` : 'Digite o nome de uma cidade'}><span>Ver dados</span><ArrowRight /></button>
            </div>
            <datalist id="home-city-options">{municipalities.map((municipality) => <option value={municipality.name} key={municipality.code} />)}</datalist>
          </form>
          <div className="hero-actions hero-actions--secondary">
            <Link href="/explorador" className="secondary-button">Explorar primeiro</Link>
            <Link href="/metodos" className="secondary-button">Como ler os dados</Link>
          </div>
          <p className="hero-method-note">Informação pública, por residência e com limitações visíveis.</p>
        </div>
        <div className="home-hero__data" aria-label="Prévia do explorador de dados">
          <div className="data-preview__heading">
            <span>Prévia dos dados</span>
            <strong>{indicator.label}</strong>
          </div>
          <div className="data-preview__visuals">
            <TerritoryMap topology={topology} compact />
            {observations.length ? (
              <TimeSeriesChart
                compact
                indicator={indicator}
                observations={observations}
                metric="crude_rate_per_100k"
                geographyLabels={{ ...catalog.geographies, rj_total: 'Estado do Rio de Janeiro' }}
                geographies={['rj_total', 'brazil_total']}
                startYear={2018}
              />
            ) : <div className="data-preview__loading" aria-live="polite">Carregando prévia da série…</div>}
          </div>
        </div>
        <div className="river-rule" aria-hidden="true">
          <svg viewBox="0 0 800 72" preserveAspectRatio="none"><path d="M0 38C90 5 130 66 220 34S350 57 430 31 560 55 640 30 720 52 800 22" /><path d="M0 51C90 18 130 79 220 47S350 70 430 44 560 68 640 43 720 65 800 35" /></svg>
        </div>
      </section>

      <section className="lenses-section">
        <h2>Três lentes para entender os dados</h2>
        <div className="lenses-row">
          <article><span className="lens-number">01</span><Map /><div><h3>Território</h3><p>Encontre qualquer uma das 92 cidades, veja contagens e taxas e compare com o RJ e o Brasil.</p><Link href="/explorador">Abrir mapa <ArrowRight /></Link></div></article>
          <article><span className="lens-number">02</span><ChartNoAxesCombined /><div><h3>Tempo</h3><p>Observe tendências, lacunas e marcos que mudam a interpretação das séries.</p><Link href="/explorador">Ver séries <ArrowRight /></Link></div></article>
          <article><span className="lens-number">03</span><Users /><div><h3>População</h3><p>Leia diferenças por idade e sexo sem confundir contagens com taxas comparáveis.</p><Link href="/perfis">Explorar perfis <ArrowRight /></Link></div></article>
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
