import { ArrowRight, ChartNoAxesCombined, Download, FileSearch, Map, Users } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useLocation } from 'wouter'
import { DiscoverySearch } from '../components/DiscoverySearch'
import { CoBrandBlock } from '../components/CoBrandBlock'
import { municipalProperties } from '../lib/municipalities'
import { usePortal } from '../context/usePortal'

export function HomePage() {
  const { catalog, topology, release } = usePortal()
  const [, navigate] = useLocation()
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const openData = (municipalityCode: string, indicatorId: string) => navigate(`/municipios/${municipalityCode}?indicador=${indicatorId}`)
  const updatedAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(release.generatedAt))
  return (
    <main>
      <section className="home-hero">
        <div className="home-hero__copy">
          <h1>Saúde no Rio de Janeiro, cidade por cidade</h1>
          <p>Dados públicos para entender, comparar e acompanhar a saúde nos 92 municípios do estado. Comece escolhendo uma cidade e um assunto.</p>
          <div className="home-discovery-intro"><strong>Comece por uma pergunta</strong><span>Escolha a cidade e o tema para receber uma resposta principal.</span></div>
          <DiscoverySearch municipalities={municipalities} indicators={catalog.indicators} onOpen={openData} />
          <div className="hero-actions hero-actions--secondary">
            <Link href="/explorador" className="secondary-button">Explorar primeiro</Link>
            <Link href="/metodos" className="secondary-button">Como ler os dados</Link>
          </div>
          <p className="hero-method-note">92 municípios · atualização {updatedAt} · dados por residência e limitações visíveis.</p>
        </div>
        <div className="home-hero__data home-hero__territory" aria-label="Cobertura estadual">
          <svg viewBox="0 0 760 460" role="img" aria-label="Representação abstrata do território do Rio de Janeiro">
            <path className="territory-blob" d="M68 246C125 192 186 205 235 164c56-46 114-25 166-66 61-48 137-25 187 17 46 39 77 98 47 145-33 51-111 39-165 75-58 39-91 96-164 78-67-17-86-75-148-81-64-7-134-28-90-86Z" />
            <path className="territory-line" d="M80 268c92-62 168 18 247-54s178-54 287 15M92 310c90-54 169 26 250-38s169-54 249-2M126 350c79-35 142 21 212-21s144-44 205-22" />
          </svg>
          <div className="territory-stat"><strong>92</strong><span>municípios do Rio de Janeiro</span></div>
        </div>
        <div className="river-rule" aria-hidden="true">
          <svg viewBox="0 0 800 72" preserveAspectRatio="none"><path d="M0 38C90 5 130 66 220 34S350 57 430 31 560 55 640 30 720 52 800 22" /><path d="M0 51C90 18 130 79 220 47S350 70 430 44 560 68 640 43 720 65 800 35" /></svg>
        </div>
      </section>

      <section className="question-rail" aria-labelledby="questions-title"><div><h2 id="questions-title">Perguntas que ajudam a entender</h2><p>Comece por uma pergunta simples e aprofunde apenas quando precisar.</p></div><Link href="/explorador?indicador=sih-pneumonia"><strong>Como está a pneumonia na minha cidade?</strong><ArrowRight /></Link><Link href="/explorador?indicador=sim-lung"><strong>Mortalidade por câncer de pulmão</strong><ArrowRight /></Link></section>

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
      <section className="home-cobrand"><CoBrandBlock /></section>
    </main>
  )
}
