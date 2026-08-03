import { ArrowRight, ChartNoAxesCombined, Download, FileText, Map, Share2, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useRoute, useSearch } from 'wouter'
import { DiscoverySearch } from '../components/DiscoverySearch'
import { LoadingState } from '../components/LoadingState'
import { SeriesInsights } from '../components/SeriesInsights'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { usePortal } from '../context/usePortal'
import { trackEvent } from '../lib/analytics'
import { loadMap, loadMunicipalitySummaries, loadMunicipalSeries, loadSeries } from '../lib/data'
import { formatMetric, statusLabel } from '../lib/format'
import { buildMunicipalComparisonSeries, rateRatio, relativeDifferenceLabel } from '../lib/municipalComparison'
import { municipalProperties } from '../lib/municipalities'
import { buildFilteredSeriesCsv, saveCsvFile } from '../lib/publicDownload'
import type { MapPayload, MunicipalitySummaryItem, Observation } from '../types'

export function MunicipalityPage() {
  const [, params] = useRoute('/municipios/:codigo')
  const requestedIndicator = new URLSearchParams(useSearch()).get('indicador')
  if (!requestedIndicator) return <MunicipalityOverview municipalityCode={params?.codigo ?? ''} />
  return <MunicipalityDetail municipalityCode={params?.codigo ?? ''} requestedIndicator={requestedIndicator} />
}

const CURATED_INDICATORS = ['sih-pneumonia', 'sim-lung', 'sim-all-malignant-neoplasms', 'sim-acute-myocardial-infarction']

function MunicipalityOverview({ municipalityCode }: { municipalityCode: string }) {
  const { catalog, topology } = usePortal()
  const [, navigate] = useLocation()
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const municipality = municipalities.find((item) => item.code === municipalityCode)
  const [items, setItems] = useState<MunicipalitySummaryItem[] | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  useEffect(() => {
    let active = true
    loadMunicipalitySummaries()
      .then((payload) => { if (active) setItems(payload.municipalities[municipalityCode] ?? []) })
      .catch(() => { if (active) setLoadFailed(true); trackEvent('data_load_error', { surface: 'municipality_overview' }) })
    return () => { active = false }
  }, [municipalityCode])
  if (!municipality) return <main className="content-page"><h1>Município não encontrado</h1><p>Use um código IBGE válido de um dos 92 municípios do Rio de Janeiro.</p><Link href="/">Voltar ao início</Link></main>
  const open = (code: string, indicatorId: string) => navigate(`/municipios/${code}?indicador=${indicatorId}`)
  return (
    <main className="municipality-page">
      <section className="municipality-hero"><Link href="/">Observatório estadual · 92 municípios</Link><h1>{municipality.name}</h1><p>Um ponto de partida neutro com indicadores selecionados de mortalidade e internações de residentes.</p><DiscoverySearch compact municipalities={municipalities} indicators={catalog.indicators} initialMunicipalityCode={municipality.code} onOpen={open} /></section>
      <section className="municipality-overview" aria-labelledby="overview-title"><div className="municipality-overview__heading"><h2 id="overview-title">Visão geral da cidade</h2><p>Escolha um indicador para entender o valor, a comparação e a evolução.</p></div>{items ? <div className="municipality-overview__list">{CURATED_INDICATORS.map((id) => {
        const indicator = catalog.indicators.find((item) => item.id === id)
        const latest = items.find((item) => item.indicatorId === id)
        if (!indicator) return null
        const protectedCell = latest?.suppressionStatus === 'suppressed'
        return <Link className="municipality-overview-card" key={id} href={`/municipios/${municipality.code}?indicador=${id}`}><span>{indicator.measureLabel}</span><h3>{indicator.label}</h3><strong>{protectedCell ? 'Dado protegido' : formatMetric(latest?.value ?? null, 'crude_rate_per_100k')}</strong><small>{latest?.period ? `${latest.period} · ${protectedCell ? 'valor não publicado' : 'taxa por 100 mil'}` : 'Sem período publicável'}</small><em>Entender este dado <ArrowRight /></em></Link>
      })}</div> : loadFailed ? <div className="municipality-inline-error"><strong>Não foi possível carregar a visão geral.</strong><button type="button" onClick={() => window.location.reload()}>Tentar novamente</button></div> : <LoadingState label="Carregando visão geral…" />}</section>
      <section className="municipality-method"><FileText /><div><h2>Como esta seleção foi feita</h2><p>Os quatro indicadores têm ordem editorial fixa. Eles não representam uma lista dos “piores” resultados nem um diagnóstico da cidade.</p><Link href="/metodos">Conhecer fontes e limitações</Link></div></section>
    </main>
  )
}

function MunicipalityDetail({ municipalityCode, requestedIndicator }: { municipalityCode: string; requestedIndicator: string }) {
  const { catalog, topology } = usePortal()
  const [, navigate] = useLocation()
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const municipality = municipalities.find((item) => item.code === municipalityCode)
  const indicator = catalog.indicators.find((item) => item.id === requestedIndicator) ?? catalog.indicators[0]
  const [summary, setSummary] = useState<MunicipalitySummaryItem | null | undefined>(undefined)
  const [series, setSeries] = useState<Observation[] | null>(null)
  const [municipalSeries, setMunicipalSeries] = useState<Observation[] | null>(null)
  const [map, setMap] = useState<MapPayload | null>(null)
  const [activeTab, setActiveTab] = useState<'evolution' | 'map' | 'profile' | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [linkCopied, setLinkCopied] = useState(false)

  useEffect(() => {
    let active = true
    setSummary(undefined); setSeries(null); setMunicipalSeries(null); setMap(null); setActiveTab(null); setDetailError(null)
    loadMunicipalitySummaries().then((payload) => {
      if (!active) return
      setSummary(payload.municipalities[municipalityCode]?.find((item) => item.indicatorId === indicator.id) ?? null)
      trackEvent('first_answer_rendered', { surface: 'municipality', indicatorId: indicator.id })
    }).catch(() => { if (active) setSummary(null); trackEvent('data_load_error', { surface: 'municipality_summary' }) })
    return () => { active = false }
  }, [indicator.id, municipalityCode])

  useEffect(() => {
    if (activeTab !== 'evolution' || (series && municipalSeries)) return
    let active = true
    setDetailError(null)
    Promise.all([loadSeries(indicator.id), loadMunicipalSeries(indicator.id)])
      .then(([seriesPayload, municipalPayload]) => { if (active) { setSeries(seriesPayload.observations); setMunicipalSeries(municipalPayload.observations) } })
      .catch(() => { if (active) setDetailError('Não foi possível carregar a evolução. Tente novamente.') })
    return () => { active = false }
  }, [activeTab, indicator.id, municipalSeries, series])

  useEffect(() => {
    if (activeTab !== 'map' || map) return
    let active = true
    setDetailError(null)
    loadMap(indicator.id).then((payload) => { if (active) setMap(payload) })
      .catch(() => { if (active) setDetailError('Não foi possível carregar o mapa. Tente novamente.'); trackEvent('data_load_error', { surface: 'municipality_map' }) })
    return () => { active = false }
  }, [activeTab, indicator.id, map])

  if (!municipality) return <main className="content-page"><h1>Município não encontrado</h1><p>Use um código IBGE válido de um dos 92 municípios do Rio de Janeiro.</p><Link href="/">Voltar ao início</Link></main>
  if (summary === undefined) return <main className="content-page"><LoadingState label={`Carregando resposta de ${municipality.name}…`} /></main>

  const latest = summary
  const period = latest?.period ?? null
  const comparisonSeries = series && municipalSeries ? buildMunicipalComparisonSeries(municipality.code, municipalSeries, series) : []
  const labels = { selected_municipality: municipality.name, rest_of_rj_excluding_selected: `RJ sem ${municipality.name}`, brazil_total: 'Brasil' }
  const ratio = rateRatio(latest?.value, latest?.restOfStateValue)
  const status = statusLabel(latest?.dataStatus ?? '')
  const open = (code: string, indicatorId: string) => navigate(`/municipios/${code}?indicador=${indicatorId}`)
  const download = async () => {
    const [seriesPayload, municipalPayload] = series && municipalSeries ? [{ observations: series }, { observations: municipalSeries }] : await Promise.all([loadSeries(indicator.id), loadMunicipalSeries(indicator.id)])
    const rows = buildMunicipalComparisonSeries(municipality.code, municipalPayload.observations, seriesPayload.observations)
    const csv = buildFilteredSeriesCsv(rows, { indicatorId: indicator.id, metric: 'crude_rate_per_100k', startYear: indicator.yearStart, endYear: indicator.yearEnd, geographies: Object.keys(labels) })
    saveCsvFile(`${municipality.name}-${indicator.id}.csv`, csv)
    trackEvent('download_completed', { surface: 'municipality' })
  }
  const share = async () => {
    await navigator.clipboard.writeText(window.location.href)
    setLinkCopied(true)
    trackEvent('share_completed', { surface: 'municipality' })
  }

  return (
    <main className="municipality-page">
      <section className="municipality-hero">
        <Link href="/">Observatório estadual · 92 municípios</Link>
        <h1>{municipality.name}</h1>
        <p>Dados de residentes, com comparação ao restante do Rio de Janeiro e ao Brasil quando a fonte é equivalente.</p>
        <DiscoverySearch compact municipalities={municipalities} indicators={catalog.indicators} initialMunicipalityCode={municipality.code} onOpen={open} />
      </section>
      <section className={`municipality-answer${latest?.suppressionStatus === 'suppressed' ? ' is-suppressed' : ''}`} aria-labelledby="municipality-answer-title">
        <div className="municipality-answer__intro"><span>O que este indicador mede</span><h2 id="municipality-answer-title">{indicator.label}</h2><p>{indicator.definition}</p><small>{indicator.measureLabel} · {period ?? 'sem período publicável'} · {status}</small></div>
        <div className="municipality-answer__value"><span>1 · Valor</span><strong>{latest?.suppressionStatus === 'suppressed' ? 'Dado protegido' : formatMetric(latest?.value ?? null, 'crude_rate_per_100k')}</strong>{latest?.suppressionStatus !== 'suppressed' ? <><span>por 100 mil habitantes</span><small>{formatMetric(latest?.count ?? null, 'count')} eventos registrados</small></> : <small>Célula pequena protegida. A ausência do valor não significa zero.</small>}</div>
        <div className="municipality-answer__comparison"><span>2 · Comparação</span><strong>{latest?.comparisonAvailable ? relativeDifferenceLabel(ratio) : 'Comparação indisponível'}</strong><small>RJ sem {municipality.name}: {formatMetric(latest?.restOfStateValue ?? null, 'crude_rate_per_100k')}</small>{indicator.comparisonAvailability?.brazil ? <small>Brasil: {formatMetric(latest?.brazilValue ?? null, 'crude_rate_per_100k')}</small> : <small>Brasil não exibido: definição ou período não equivalentes.</small>}</div>
      </section>
      <div className="municipality-actions"><button type="button" onClick={download}><Download />Baixar este recorte</button><button type="button" onClick={share}><Share2 />{linkCopied ? 'Link copiado' : 'Copiar link'}</button><Link href={`/explorador?indicador=${indicator.id}&municipio=${municipality.code}`}>Abrir análise avançada <ArrowRight /></Link></div>
      <section className="municipality-explore" aria-labelledby="explore-title">
        <div className="municipality-explore__heading"><span>3 · Evolução e contexto</span><h2 id="explore-title">Explore quando precisar</h2><p>A resposta principal está acima. Abra apenas a visualização que ajuda sua pergunta.</p></div>
        <div className="municipality-tabs" role="tablist" aria-label="Detalhes do indicador">
          <button type="button" role="tab" aria-selected={activeTab === 'evolution'} onClick={() => { setActiveTab('evolution'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'evolution' }) }}><ChartNoAxesCombined />Evolução</button>
          <button type="button" role="tab" aria-selected={activeTab === 'map'} onClick={() => { setActiveTab('map'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'map' }) }}><Map />Mapa</button>
          <button type="button" role="tab" aria-selected={activeTab === 'profile'} onClick={() => { setActiveTab('profile'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'profile' }) }}><Users />Perfil</button>
        </div>
        <div className="municipality-tabpanel" role="tabpanel">
          {!activeTab ? <div className="municipality-tab-empty"><strong>Nenhuma visualização carregada</strong><p>Escolha evolução, mapa ou perfil para continuar.</p></div> : null}
          {activeTab === 'evolution' ? series && municipalSeries ? <div><SeriesInsights municipalityName={municipality.name} observations={comparisonSeries} /><TimeSeriesChart indicator={indicator} observations={comparisonSeries} metric="crude_rate_per_100k" geographyLabels={labels} geographies={Object.keys(labels)} startYear={indicator.yearStart} endYear={indicator.yearEnd} /></div> : detailError ? <div className="municipality-inline-error"><strong>{detailError}</strong><button type="button" onClick={() => { setActiveTab(null); setTimeout(() => setActiveTab('evolution'), 0) }}>Tentar novamente</button></div> : <LoadingState label="Carregando evolução…" /> : null}
          {activeTab === 'map' ? map ? <TerritoryMap topology={topology} values={map.values} scaleDomain={map.mapScale?.domain} status={map.status} period={map.period} selectedCode={municipality.code} onSelect={(code) => navigate(`/municipios/${code}?indicador=${indicator.id}`)} /> : detailError ? <div className="municipality-inline-error"><strong>{detailError}</strong><button type="button" onClick={() => { setActiveTab(null); setTimeout(() => setActiveTab('map'), 0) }}>Tentar novamente</button></div> : <LoadingState label="Carregando mapa contextual…" /> : null}
          {activeTab === 'profile' ? <div className="municipality-profile-callout"><Users /><div><strong>Perfil por idade e sexo</strong><p>{indicator.profileCoverage?.status === 'available' ? 'Há perfil municipal publicável para 2022.' : 'Este perfil ainda não está disponível para a fonte selecionada.'}</p>{indicator.profileCoverage?.status === 'available' ? <Link href={`/perfis?municipio=${municipality.code}&indicador=${indicator.id}&periodo=2022`}>Abrir perfil de 2022 <ArrowRight /></Link> : <Link href={`/indicadores/${indicator.id}`}>Entender a indisponibilidade</Link>}</div></div> : null}
        </div>
      </section>
      <section className="municipality-method"><FileText /><div><h2>Como interpretar</h2><p><strong>O que permite concluir:</strong> {indicator.allowsConclusion}</p><p><strong>O que não permite concluir:</strong> {indicator.doesNotAllowConclusion}</p><Link href={`/indicadores/${indicator.id}`}>Ver fonte, CID e limitações</Link></div></section>
    </main>
  )
}
