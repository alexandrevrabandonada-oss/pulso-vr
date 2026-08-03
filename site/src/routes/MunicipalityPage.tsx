import { ArrowRight, ChartNoAxesCombined, Download, FileText, Map, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useRoute, useSearch } from 'wouter'
import { DiscoverySearch } from '../components/DiscoverySearch'
import { DataGlossary } from '../components/DataGlossary'
import { LoadingState } from '../components/LoadingState'
import { SeriesInsights } from '../components/SeriesInsights'
import { ShareButton } from '../components/ShareButton'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { usePortal } from '../context/usePortal'
import { trackEvent } from '../lib/analytics'
import { loadMap, loadMunicipalitySummary, loadMunicipalSeries, loadSeries } from '../lib/data'
import { formatMetric, metricLabel, statusLabel } from '../lib/format'
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
    loadMunicipalitySummary(municipalityCode)
      .then((payload) => { if (active) setItems(payload.items) })
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
         const cardMetric = latest?.metricKind ?? 'crude_rate_per_100k'
         return <Link className="municipality-overview-card" key={id} href={`/municipios/${municipality.code}?indicador=${id}`}><span>{indicator.measureLabel}</span><h3>{indicator.label}</h3><strong>{protectedCell ? 'Dado protegido' : formatMetric(latest?.value ?? null, cardMetric)}</strong><small>{latest?.period ? `${latest.period} · ${protectedCell ? 'valor não publicado' : metricLabel(cardMetric)}` : 'Sem período publicável'}</small><em>Entender este dado <ArrowRight /></em></Link>
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
  const [mapMetric, setMapMetric] = useState<'age_sex_standardized_rate_per_100k' | 'crude_rate_per_100k'>('age_sex_standardized_rate_per_100k')
  const [activeTab, setActiveTab] = useState<'evolution' | 'map' | 'profile' | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setSummary(undefined); setSeries(null); setMunicipalSeries(null); setMap(null); setMapMetric('age_sex_standardized_rate_per_100k'); setActiveTab(null); setDetailError(null)
    loadMunicipalitySummary(municipalityCode).then((payload) => {
      if (!active) return
      setSummary(payload.items.find((item) => item.indicatorId === indicator.id) ?? null)
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
  if (summary === null) return <main className="content-page"><h1>Resposta temporariamente indisponível</h1><p>Não foi possível carregar o resumo de {indicator.label} para {municipality.name}. Nenhum valor foi substituído por zero.</p><button type="button" onClick={() => window.location.reload()}>Tentar novamente</button></main>

  const latest = summary
  const answerMetric = latest.metricKind ?? 'crude_rate_per_100k'
  const isNeurological = indicator.theme === 'neurological'
  const period = latest?.period ?? null
  const crudeMunicipalSeries = municipalSeries?.filter((item) => item.metricKind === 'crude_rate_per_100k') ?? null
  const comparisonSeries = series && crudeMunicipalSeries ? buildMunicipalComparisonSeries(municipality.code, crudeMunicipalSeries, series.filter((item) => item.metricKind === 'crude_rate_per_100k')) : []
  const labels = { selected_municipality: municipality.name, rest_of_rj_excluding_selected: `RJ sem ${municipality.name}`, brazil_total: 'Brasil' }
  const ratio = rateRatio(latest?.value, latest?.restOfStateValue)
  const status = statusLabel(latest.dataStatus)
  const mapAlternative = map?.alternatives?.find((item) => item.metricKind === 'crude_rate_per_100k')
  const visibleMapValues = mapMetric === 'crude_rate_per_100k' && mapAlternative ? mapAlternative.values : map?.values ?? []
  const visibleMapPeriod = mapMetric === 'crude_rate_per_100k' && mapAlternative ? mapAlternative.period : map?.period
  const eventLabel = indicator.measure === 'hospitalization'
    ? 'internações/AIHs registradas'
    : indicator.measure === 'ambulatory_production'
      ? 'procedimentos registrados'
      : 'óbitos de residentes registrados'
  const heroDescription = indicator.measure === 'hospitalization'
    ? 'Internações/AIHs de residentes registradas pela fonte.'
    : indicator.measure === 'ambulatory_production'
      ? 'Produção ambulatorial registrada pela fonte, quando a dimensão diagnóstica está validada.'
      : 'Óbitos de residentes registrados pela causa básica na fonte.'
  const geographyLabel = indicator.geographyBasis === 'establishment' ? 'Local do estabelecimento' : 'Município de residência'
  const comparisonLabel = latest?.comparisonAvailable ? `${relativeDifferenceLabel(ratio)} do restante do RJ` : 'Comparação indisponível'
  const open = (code: string, indicatorId: string) => navigate(`/municipios/${code}?indicador=${indicatorId}`)
  const download = async () => {
    const [seriesPayload, municipalPayload] = series && municipalSeries ? [{ observations: series }, { observations: municipalSeries }] : await Promise.all([loadSeries(indicator.id), loadMunicipalSeries(indicator.id)])
    const rows = buildMunicipalComparisonSeries(municipality.code, municipalPayload.observations, seriesPayload.observations)
    const csv = buildFilteredSeriesCsv(rows, { indicatorId: indicator.id, metric: 'crude_rate_per_100k', startYear: indicator.yearStart, endYear: indicator.yearEnd, geographies: Object.keys(labels) })
    saveCsvFile(`${municipality.name}-${indicator.id}.csv`, csv)
    trackEvent('download_completed', { surface: 'municipality' })
  }

  return (
    <main className="municipality-page">
      <section className="municipality-hero">
        <Link href="/">Observatório estadual · 92 municípios</Link>
        <h1>{municipality.name}</h1>
        <p>{heroDescription} Compare com o restante do Rio de Janeiro e com o Brasil quando a fonte é equivalente.</p>
        <DiscoverySearch compact municipalities={municipalities} indicators={catalog.indicators} initialMunicipalityCode={municipality.code} onOpen={open} />
      </section>
      <section className={`municipality-answer${latest?.suppressionStatus === 'suppressed' ? ' is-suppressed' : ''}`} aria-labelledby="municipality-answer-title">
        <div className="municipality-answer__intro">
          <div className="answer-kicker"><span>Leia primeiro</span><strong>O que este indicador mede</strong></div>
          <h2 id="municipality-answer-title">{indicator.label}</h2>
          <p>{indicator.definition}</p>
          <dl className="answer-meta">
            <div><dt>Fonte</dt><dd>{indicator.sourceLabel}</dd></div>
            <div><dt>Período</dt><dd>{period ?? 'Sem período publicável'}</dd></div>
            <div><dt>Território</dt><dd>{geographyLabel}</dd></div>
            <div><dt>Status</dt><dd>{status}</dd></div>
          </dl>
        </div>
        <div className="municipality-answer__value">
          <div className="answer-kicker"><span>1</span><strong>Resultado principal</strong></div>
          <strong className="answer-number">{latest.suppressionStatus === 'suppressed' ? 'Dado protegido' : formatMetric(latest.value, answerMetric)}</strong>
          {latest.suppressionStatus !== 'suppressed' ? <>
            <span className="answer-unit">{metricLabel(answerMetric)}</span>
            <small>{formatMetric(latest.count, 'count')} {eventLabel}</small>
          </> : <small>Célula pequena protegida. A ausência do valor não significa zero.</small>}
        </div>
        <div className="municipality-answer__comparison">
          <div className="answer-kicker"><span>2</span><strong>Compare com cuidado</strong></div>
          <strong className="answer-comparison-headline">{comparisonLabel}</strong>
          <p className="answer-helper">A referência estadual é o RJ sem {municipality.name}; não é uma média simples das cidades.</p>
          <div className="answer-comparison-list">
            <div><span>RJ sem {municipality.name}</span><strong>{latest?.comparisonAvailable ? formatMetric(latest.restOfStateValue, answerMetric) : 'Indisponível'}</strong></div>
            {indicator.comparisonAvailability?.brazil && answerMetric !== 'age_sex_standardized_rate_per_100k' ? <div><span>Brasil</span><strong>{formatMetric(latest?.brazilValue ?? null, answerMetric)}</strong></div> : <div className="is-unavailable"><span>Brasil</span><strong>Não exibido</strong><small>Definição, métrica ou período não equivalentes.</small></div>}
          </div>
        </div>
        <div className="municipality-answer__interpretation">
          <div className="answer-kicker"><span>3</span><strong>Como ler</strong></div>
          <h3>Uma leitura orientada pelo contexto</h3>
          <p>{indicator.allowsConclusion}</p>
          <div className="answer-boundary"><strong>Este dado não permite concluir:</strong><p>{indicator.doesNotAllowConclusion}</p></div>
        </div>
      </section>
      {isNeurological ? <section className="municipality-method"><FileText /><div><h2>Por que padronizar?</h2><p>Municípios mais envelhecidos podem apresentar taxas brutas maiores apenas pela composição etária. A taxa de 2022 ajusta idade e sexo usando a população do Brasil no Censo 2022, tornando a comparação municipal mais justa. Ela não mede prevalência nem todas as pessoas com diagnóstico.</p><p><strong>Dado recente:</strong> a mortalidade bruta de 2024 aparece na evolução. O ano de 2023 permanece como lacuna e não é interpolado.</p></div></section> : null}
      <div className="municipality-actions"><button type="button" onClick={download}><Download />Baixar este recorte</button><ShareButton surface="municipality" context={{ municipalityCode: municipality.code, indicatorId: indicator.id, period: period ?? undefined, metricKind: answerMetric, template: 'answer', format: 'og', route: 'municipality' }} /><Link href={`/explorador?indicador=${indicator.id}&municipio=${municipality.code}`}>Abrir análise avançada <ArrowRight /></Link></div>
       <section className="municipality-explore" aria-labelledby="explore-title">
         <div className="municipality-explore__heading"><span>Aprofunde se quiser</span><h2 id="explore-title">Explore quando precisar</h2><p>A resposta principal está acima. Abra apenas a visualização que ajuda sua pergunta.</p></div>
        <div className="municipality-tabs glass-surface" role="tablist" aria-label="Detalhes do indicador">
          <button type="button" role="tab" aria-selected={activeTab === 'evolution'} onClick={() => { setActiveTab('evolution'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'evolution' }) }}><ChartNoAxesCombined />Evolução</button>
          <button type="button" role="tab" aria-selected={activeTab === 'map'} onClick={() => { setActiveTab('map'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'map' }) }}><Map />Mapa</button>
          <button type="button" role="tab" aria-selected={activeTab === 'profile'} onClick={() => { setActiveTab('profile'); trackEvent('map_series_toggled', { surface: 'municipality', tab: 'profile' }) }}><Users />Perfil</button>
        </div>
        <div className="municipality-tabpanel" role="tabpanel">
          {activeTab === 'evolution' || activeTab === 'map' ? <div className="visual-share"><ShareButton surface={`municipality_${activeTab}`} label={`Compartilhar ${activeTab === 'map' ? 'mapa' : 'evolução'}`} context={{ municipalityCode: municipality.code, indicatorId: indicator.id, period: activeTab === 'map' ? visibleMapPeriod : period ?? undefined, metricKind: activeTab === 'map' ? mapMetric : 'crude_rate_per_100k', template: activeTab, format: 'og', route: 'municipality' }} /></div> : null}
          {!activeTab ? <div className="municipality-tab-empty"><strong>Nenhuma visualização carregada</strong><p>Escolha evolução, mapa ou perfil para continuar.</p></div> : null}
          {activeTab === 'evolution' ? series && municipalSeries ? <div>{isNeurological ? <p>A evolução abaixo usa exclusivamente a taxa bruta. A linha é interrompida em 2023 e não se conecta à taxa padronizada de 2022.</p> : null}<SeriesInsights municipalityName={municipality.name} observations={comparisonSeries} /><TimeSeriesChart indicator={indicator} observations={comparisonSeries} metric="crude_rate_per_100k" geographyLabels={labels} geographies={Object.keys(labels)} startYear={indicator.yearStart} endYear={indicator.yearEnd} /></div> : detailError ? <div className="municipality-inline-error"><strong>{detailError}</strong><button type="button" onClick={() => { setActiveTab(null); setTimeout(() => setActiveTab('evolution'), 0) }}>Tentar novamente</button></div> : <LoadingState label="Carregando evolução…" /> : null}
          {activeTab === 'map' ? map ? <div>{isNeurological && mapAlternative ? <div className="metric-switch" role="group" aria-label="Métrica do mapa"><button type="button" className={mapMetric === 'age_sex_standardized_rate_per_100k' ? 'is-selected' : ''} onClick={() => setMapMetric('age_sex_standardized_rate_per_100k')}>Padronizada · 2022</button><button type="button" className={mapMetric === 'crude_rate_per_100k' ? 'is-selected' : ''} onClick={() => setMapMetric('crude_rate_per_100k')}>Bruta · 2024</button></div> : null}<TerritoryMap topology={topology} values={visibleMapValues} scaleDomain={mapMetric === 'age_sex_standardized_rate_per_100k' ? map.mapScale?.domain : undefined} status={map.status} period={visibleMapPeriod} selectedCode={municipality.code} onSelect={(code) => navigate(`/municipios/${code}?indicador=${indicator.id}`)} /></div> : detailError ? <div className="municipality-inline-error"><strong>{detailError}</strong><button type="button" onClick={() => { setActiveTab(null); setTimeout(() => setActiveTab('map'), 0) }}>Tentar novamente</button></div> : <LoadingState label="Carregando mapa contextual…" /> : null}
          {activeTab === 'profile' ? <div className="municipality-profile-callout"><Users /><div><strong>Perfil por idade e sexo</strong><p>{indicator.profileCoverage?.status === 'available' ? 'Há perfil municipal publicável para 2022.' : 'Este perfil ainda não está disponível para a fonte selecionada.'}</p>{indicator.profileCoverage?.status === 'available' ? <Link href={`/perfis?municipio=${municipality.code}&indicador=${indicator.id}&periodo=2022`}>Abrir perfil de 2022 <ArrowRight /></Link> : <Link href={`/indicadores/${indicator.id}`}>Entender a indisponibilidade</Link>}</div></div> : null}
        </div>
      </section>
      {isNeurological ? <section className="municipality-method"><FileText /><div><h2>Outras camadas disponíveis</h2><p><strong>Internações registradas em 2022:</strong> consulte o indicador SIH correspondente. Cada registro é uma AIH/evento de internação, não uma pessoa única ou caso novo.</p>{catalog.indicators.some((item) => item.id === `sih-${indicator.outcomeId.replaceAll('_', '-')}`) ? <Link href={`/municipios/${municipality.code}?indicador=sih-${indicator.outcomeId.replaceAll('_', '-')}`}>Ver internações/AIHs de 2022</Link> : null}<p><strong>Produção ambulatorial SIA:</strong> indisponível nesta release porque não há dimensão diagnóstica CID-10 e território de residência validados. Ausência não significa zero.</p></div></section> : null}
      <DataGlossary />
      <section className="municipality-method"><FileText /><div><h2>Fonte e limites</h2><p><strong>Fonte:</strong> {indicator.sourceLabel} · <strong>Território:</strong> {geographyLabel}.</p><p><strong>O que não permite concluir:</strong> {indicator.doesNotAllowConclusion}</p><Link href={`/indicadores/${indicator.id}`}>Ver fonte, CID e limitações</Link></div></section>
    </main>
  )
}
