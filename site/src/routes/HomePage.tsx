import { ArrowRight, ChartNoAxesCombined, Download, FileSearch, Map, Users } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useLocation } from 'wouter'
import { DiscoverySearch } from '../components/DiscoverySearch'
import { TerritoryMap } from '../components/TerritoryMap'
import { municipalProperties } from '../lib/municipalities'
import { usePortal } from '../context/usePortal'

export function HomePage() {
  const { catalog, topology, release } = usePortal()
  const [, navigate] = useLocation()
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const openCity = (municipalityCode: string, indicatorId: string) => navigate(`/municipios/${municipalityCode}?indicador=${indicatorId}`)
  const updatedAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(release.generatedAt))
  return (
    <main>
      <section className="home-hero">
        <div className="home-hero__copy">
          <p className="hero-eyebrow">Observatório estadual de saúde</p>
          <h1>Doenças no Rio de Janeiro, cidade por cidade</h1>
          <p>Escolha qualquer uma das 92 cidades, consulte internações e óbitos por residência e compare sua taxa com o restante do estado e com o Brasil.</p>
          <DiscoverySearch municipalities={municipalities} indicators={catalog.indicators} onOpen={openCity} />
          <div className="hero-actions hero-actions--secondary">
            <Link href="/explorador" className="secondary-button">Explorar primeiro</Link>
            <Link href="/metodos" className="secondary-button">Como ler os dados</Link>
          </div>
          <p className="hero-method-note">92 municípios · atualização {updatedAt} · dados por residência e limitações visíveis.</p>
        </div>
        <div className="home-hero__data" aria-label="Prévia do explorador de dados">
          <div className="data-preview__heading">
            <span>Prévia dos dados</span>
            <strong>Todos os municípios, sem cidade padrão</strong>
          </div>
          <div className="data-preview__visuals">
            <TerritoryMap topology={topology} compact />
            <div className="home-examples"><strong>Perguntas que você pode responder</strong><Link href="/explorador?indicador=sih-pneumonia">Como está a pneumonia?</Link><Link href="/explorador?indicador=sim-lung">Mortalidade por câncer de pulmão</Link><Link href="/explorador">Comparar uma cidade com o restante do RJ</Link></div>
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
