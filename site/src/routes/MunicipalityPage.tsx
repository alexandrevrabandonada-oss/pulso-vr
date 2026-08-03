import { ArrowRight, Download, FileText, Share2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useRoute, useSearch } from 'wouter'
import { DiscoverySearch } from '../components/DiscoverySearch'
import { LoadingState } from '../components/LoadingState'
import { SeriesInsights } from '../components/SeriesInsights'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { usePortal } from '../context/usePortal'
import { trackEvent } from '../lib/analytics'
import { loadMap, loadMunicipalSeries, loadSeries } from '../lib/data'
import { formatMetric, statusLabel } from '../lib/format'
import { buildMunicipalComparisonSeries, rateRatio, relativeDifferenceLabel, restOfStateExcludingMunicipality } from '../lib/municipalComparison'
import { municipalProperties } from '../lib/municipalities'
import { buildFilteredSeriesCsv, saveCsvFile } from '../lib/publicDownload'
import type { MapPayload, Observation } from '../types'

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
  const [payloads, setPayloads] = useState<Record<string, Observation[]> | null>(null)
  useEffect(() => {
    let active = true
    Promise.all(CURATED_INDICATORS.map(async (id) => [id, (await loadMunicipalSeries(id)).observations] as const))
      .then((entries) => { if (active) setPayloads(Object.fromEntries(entries)) })
      .catch(() => trackEvent('data_load_error', { surface: 'municipality_overview' }))
    return () => { active = false }
  }, [])
  if (!municipality) return <main className="content-page"><h1>Município não encontrado</h1><p>Use um código IBGE válido de um dos 92 municípios do Rio de Janeiro.</p><Link href="/">Voltar ao início</Link></main>
  const open = (code: string, indicatorId: string) => navigate(`/municipios/${code}?indicador=${indicatorId}`)
  return (
    <main className="municipality-page">
      <section className="municipality-hero"><Link href="/">Observatório estadual · 92 municípios</Link><h1>{municipality.name}</h1><p>Um ponto de partida neutro com indicadores selecionados de mortalidade e internações de residentes.</p><DiscoverySearch compact municipalities={municipalities} indicators={catalog.indicators} initialMunicipalityCode={municipality.code} onOpen={open} /></section>
      <section className="municipality-overview" aria-labelledby="overview-title"><div className="municipality-overview__heading"><h2 id="overview-title">Visão geral da cidade</h2><p>Escolha um indicador para entender o valor, a evolução e as comparações disponíveis.</p></div>{payloads ? <div className="municipality-overview__list">{CURATED_INDICATORS.map((id) => {
        const indicator = catalog.indicators.find((item) => item.id === id)
        const rows = payloads[id]?.filter((item) => item.geographyId === municipality.code) ?? []
        const latest = [...rows].reverse().find((item) => item.value !== null || item.suppressed)
        if (!indicator) return null
        return <Link className="municipality-overview-card" key={id} href={`/municipios/${municipality.code}?indicador=${id}`}><span>{indicator.measureLabel}</span><h3>{indicator.label}</h3><strong>{latest?.suppressed ? 'Não publicado' : formatMetric(latest?.value ?? null, 'crude_rate_per_100k')}</strong><small>{latest?.period ?? 'Sem período publicável'} · por 100 mil</small><em>Entender este dado <ArrowRight /></em></Link>
      })}</div> : <LoadingState label="Carregando visão geral…" />}</section>
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
  const [series, setSeries] = useState<Observation[] | null>(null)
  const [municipalSeries, setMunicipalSeries] = useState<Observation[] | null>(null)
  const [map, setMap] = useState<MapPayload | null>(null)

  useEffect(() => {
    let active = true
    setSeries(null); setMunicipalSeries(null); setMap(null)
    Promise.all([loadSeries(indicator.id), loadMunicipalSeries(indicator.id)])
      .then(([seriesPayload, municipalPayload]) => {
        if (!active) return
        setSeries(seriesPayload.observations)
        setMunicipalSeries(municipalPayload.observations)
        trackEvent('first_answer_rendered', { surface: 'municipality', indicatorId: indicator.id })
        loadMap(indicator.id).then((mapPayload) => { if (active) setMap(mapPayload) })
          .catch(() => trackEvent('data_load_error', { surface: 'municipality_map' }))
      }).catch(() => trackEvent('data_load_error', { surface: 'municipality' }))
    return () => { active = false }
  }, [indicator.id])

  if (!municipality) return <main className="content-page"><h1>Município não encontrado</h1><p>Use um código IBGE válido de um dos 92 municípios do Rio de Janeiro.</p><Link href="/">Voltar ao início</Link></main>
  if (!series || !municipalSeries) return <main className="content-page"><LoadingState label={`Carregando dados de ${municipality.name}…`} /></main>

  const cityRows = municipalSeries.filter((item) => item.geographyId === municipality.code)
  const latest = [...cityRows].reverse().find((item) => item.value !== null || item.suppressed) ?? null
  const period = latest?.period ?? map?.period ?? null
  const stateTotal = series.find((item) => item.geographyId === 'rj_total' && item.period === period) ?? null
  const brazil = series.find((item) => item.geographyId === 'brazil_total' && item.period === period) ?? null
  const rest = restOfStateExcludingMunicipality(latest, stateTotal)
  const comparisonSeries = buildMunicipalComparisonSeries(municipality.code, municipalSeries, series)
  const labels = { selected_municipality: municipality.name, rest_of_rj_excluding_selected: `RJ sem ${municipality.name}`, brazil_total: 'Brasil' }
  const ratio = rateRatio(latest?.value, rest?.value)
  const status = statusLabel(latest?.dataStatus ?? '')
  const open = (code: string, indicatorId: string) => navigate(`/municipios/${code}?indicador=${indicatorId}`)
  const download = () => {
    const csv = buildFilteredSeriesCsv(comparisonSeries, { indicatorId: indicator.id, metric: 'crude_rate_per_100k', startYear: indicator.yearStart, endYear: indicator.yearEnd, geographies: Object.keys(labels) })
    saveCsvFile(`${municipality.name}-${indicator.id}.csv`, csv)
    trackEvent('download_completed', { surface: 'municipality' })
  }
  const share = async () => {
    await navigator.clipboard.writeText(window.location.href)
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
      <section className={`municipality-answer${latest?.suppressed ? ' is-suppressed' : ''}`} aria-labelledby="municipality-answer-title">
        <div><span>{indicator.measureLabel} · {period ?? 'sem período publicável'} · {status}</span><h2 id="municipality-answer-title">{indicator.label}</h2><p>{indicator.definition}</p></div>
        <div className="municipality-answer__value"><strong>{latest?.suppressed ? 'Não publicado' : formatMetric(latest?.value ?? null, 'crude_rate_per_100k')}</strong><span>por 100 mil habitantes</span><small>{latest?.suppressed ? 'Célula pequena protegida; o valor não é zero.' : `${formatMetric(latest?.count ?? null, 'count')} eventos registrados`}</small></div>
        <div className="municipality-answer__comparison"><span>Comparação estadual</span><strong>{relativeDifferenceLabel(ratio)}</strong><small>RJ sem {municipality.name}: {formatMetric(rest?.value ?? null, 'crude_rate_per_100k')}</small><small>Brasil: {formatMetric(brazil?.value ?? null, 'crude_rate_per_100k')}</small></div>
      </section>
      <div className="municipality-actions"><button type="button" onClick={download}><Download />Baixar este recorte</button><button type="button" onClick={share}><Share2 />Copiar link</button><Link href={`/explorador?indicador=${indicator.id}&municipio=${municipality.code}`}>Abrir análise avançada <ArrowRight /></Link></div>
      <section className="municipality-visuals">
        <div><SeriesInsights municipalityName={municipality.name} observations={comparisonSeries} /><TimeSeriesChart indicator={indicator} observations={comparisonSeries} metric="crude_rate_per_100k" geographyLabels={labels} geographies={Object.keys(labels)} startYear={indicator.yearStart} endYear={indicator.yearEnd} /></div>
        {map ? <TerritoryMap topology={topology} values={map.values} scaleDomain={map.mapScale?.domain} status={map.status} period={map.period} selectedCode={municipality.code} onSelect={(code) => navigate(`/municipios/${code}?indicador=${indicator.id}`)} /> : <LoadingState label="Carregando mapa contextual…" />}
      </section>
      <section className="municipality-method"><FileText /><div><h2>Como interpretar</h2><p>{indicator.allowsConclusion} {indicator.doesNotAllowConclusion}</p><p><strong>Perfis por idade e sexo:</strong> {indicator.profileCoverage?.status === 'available' ? <Link href={`/perfis?municipio=${municipality.code}&indicador=${indicator.id}&periodo=2022`}>ver perfil municipal de 2022</Link> : 'indisponível para esta fonte, com o motivo registrado na cobertura.'}</p><Link href={`/indicadores/${indicator.id}`}>Ver fonte, CID e limitações</Link></div></section>
    </main>
  )
}
