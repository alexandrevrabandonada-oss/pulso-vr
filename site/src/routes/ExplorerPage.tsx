import { ArrowRight, ChevronDown, FileText, Info, MapPin } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearch } from 'wouter'
import { ExplorerFilters } from '../components/ExplorerFilters'
import { IndicatorFinder } from '../components/IndicatorFinder'
import { LoadingState } from '../components/LoadingState'
import { MunicipalTable } from '../components/MunicipalTable'
import { MunicipalityPicker } from '../components/MunicipalityPicker'
import { StatusNotice } from '../components/StatusNotice'
import { SeriesInsights } from '../components/SeriesInsights'
import { ShareButton } from '../components/ShareButton'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { usePortal } from '../context/usePortal'
import { loadMap, loadMunicipalSeries, loadSeries } from '../lib/data'
import { trackEvent } from '../lib/analytics'
import { deriveExplorerState, explorerStateSearch } from '../lib/explorerState'
import { formatMetric, metricLabel, statusLabel } from '../lib/format'
import { buildMunicipalComparisonSeries, rateRatio, relativeDifferenceLabel, restOfStateExcludingMunicipality } from '../lib/municipalComparison'
import { municipalProperties } from '../lib/municipalities'
import { buildFilteredSeriesCsv, saveCsvFile } from '../lib/publicDownload'
import type { Observation, Theme } from '../types'

const LEGACY_AGGREGATE_GEO_ORDER = ['volta_redonda', 'rest_of_rj_excluding_vr', 'brazil_total']

export function ExplorerPage() {
  const { catalog, release, topology } = usePortal()
  const [, navigate] = useLocation()
  const search = useSearch()
  const searchParams = useMemo(() => new URLSearchParams(search), [search])
  const explorerState = useMemo(
    () => deriveExplorerState(search, catalog.indicators),
    [search, catalog.indicators],
  )
  const { indicator, theme, metric, territory, municipalityCode, mapPeriod: requestedMapPeriod, startYear, endYear } = explorerState
  const [observations, setObservations] = useState<Observation[] | null>(null)
  const [mapPayload, setMapPayload] = useState<{ values: import('../types').MapValue[]; status: string; scaleDomain?: [number, number] | null } | null>(null)
  const [municipalObservations, setMunicipalObservations] = useState<Observation[] | null>(null)
  const [selectedMapPeriod, setSelectedMapPeriod] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'map' | 'series'>('series')
  const activeGeographies = territory === 'all' ? LEGACY_AGGREGATE_GEO_ORDER : LEGACY_AGGREGATE_GEO_ORDER.filter((id) => id === territory)
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const selectedMunicipalityCode = useMemo(
    () => municipalities.some((item) => item.code === municipalityCode) ? municipalityCode : null,
    [municipalities, municipalityCode],
  )
  const selectedMunicipality = municipalities.find((item) => item.code === selectedMunicipalityCode) ?? null
  const availableMapPeriods = useMemo(() => [...new Set((municipalObservations ?? []).filter((item) => item.metricKind === metric).map((item) => item.period))].sort((a, b) => Number(a) - Number(b)), [metric, municipalObservations])
  const municipalPeriod = selectedMapPeriod ?? mapPayload?.values[0]?.period ?? null
  const mapValues = useMemo(() => municipalPeriod && municipalObservations
    ? municipalObservations.filter((item) => item.period === municipalPeriod && item.metricKind === metric)
    : mapPayload?.values ?? [], [mapPayload, metric, municipalObservations, municipalPeriod])
  const selectedMunicipalValue = mapValues.find((item) => item.geographyId === selectedMunicipalityCode) ?? null

  useEffect(() => {
    const canonicalSearch = explorerStateSearch(explorerState)
    if (canonicalSearch !== search) navigate(`/explorador?${canonicalSearch}`, { replace: true })
  }, [explorerState, navigate, search])

  useEffect(() => {
    let active = true
    setObservations(null)
    setMapPayload(null); setMunicipalObservations(null); setSelectedMapPeriod(null)
    loadSeries(indicator.id).then((seriesPayload) => { if (active) setObservations(seriesPayload.observations) })
    return () => { active = false }
  }, [indicator.id])

  useEffect(() => {
    if (activeTab !== 'map' || (mapPayload && municipalObservations)) return
    let active = true
    Promise.all([loadMap(indicator.id), loadMunicipalSeries(indicator.id)]).then(([nextMap, municipalSeries]) => {
      if (active) {
        setMapPayload({ values: nextMap.values, status: nextMap.status, scaleDomain: nextMap.mapScale?.domain })
        setMunicipalObservations(municipalSeries.observations)
        setSelectedMapPeriod(nextMap.period ?? municipalSeries.periods.at(-1) ?? null)
      }
    }).catch(() => trackEvent('data_load_error', { surface: 'explorer_map' }))
    return () => { active = false }
  }, [activeTab, indicator.id, mapPayload, municipalObservations])

  useEffect(() => {
    if (activeTab !== 'series' || !selectedMunicipalityCode || municipalObservations) return
    let active = true
    loadMunicipalSeries(indicator.id).then((payload) => { if (active) setMunicipalObservations(payload.observations) })
      .catch(() => trackEvent('data_load_error', { surface: 'explorer_series' }))
    return () => { active = false }
  }, [activeTab, indicator.id, municipalObservations, selectedMunicipalityCode])

  useEffect(() => {
    if (requestedMapPeriod && availableMapPeriods.includes(requestedMapPeriod)) {
      setSelectedMapPeriod(requestedMapPeriod)
    }
  }, [availableMapPeriods, requestedMapPeriod])

  const update = (changes: Record<string, string | number>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => next.set(key, String(value)))
    navigate(`/explorador?${next.toString()}`, { replace: true })
  }
  const selectMunicipality = (code: string) => update({ municipio: code })
  const onTheme = (value: Theme) => {
    const nextIndicator = catalog.indicators.find((item) => item.theme === value)!
    navigate(`/explorador?${new URLSearchParams({
      tema: value,
      indicador: nextIndicator.id,
      medida: nextIndicator.availableMetrics[0] ?? 'crude_rate_per_100k',
      territorio: 'all',
      inicio: String(nextIndicator.yearStart),
      fim: String(nextIndicator.yearEnd),
      ...(municipalityCode ? { municipio: municipalityCode } : {}),
    }).toString()}`)
  }
  const onIndicator = (value: string) => {
    const nextIndicator = catalog.indicators.find((item) => item.id === value)!
    const next = new URLSearchParams(searchParams)
    next.set('indicador', value)
    next.set('tema', nextIndicator.theme)
    next.set('inicio', String(nextIndicator.yearStart))
    next.set('fim', String(nextIndicator.yearEnd))
    next.set('medida', nextIndicator.availableMetrics[0] ?? 'crude_rate_per_100k')
    next.delete('ano_mapa')
    navigate(`/explorador?${next.toString()}`)
  }
  const selectMapPeriod = (period: string) => {
    setSelectedMapPeriod(period)
    update({ ano_mapa: period })
  }

  const quickReading = useMemo(() => {
    if (selectedMunicipality && selectedMunicipalValue && municipalPeriod) {
      const stateTotal = observations?.find((item) => item.geographyId === 'rj_total' && item.period === municipalPeriod && item.metricKind === metric) ?? null
      const restOfState = restOfStateExcludingMunicipality(selectedMunicipalValue, stateTotal)
      const brazil = observations?.find((item) => item.geographyId === 'brazil_total' && item.period === municipalPeriod && item.metricKind === metric) ?? null
      const selectedValue = metric === 'count' ? selectedMunicipalValue.count : selectedMunicipalValue.value
      const difference = rateRatio(selectedMunicipalValue.value, restOfState?.value)
      const eventLabel = indicator.measure === 'hospitalization' ? 'internações hospitalares' : 'óbitos'
      return {
        year: municipalPeriod,
        headline: selectedMunicipalValue.suppressed
          ? `${selectedMunicipality.name}: dado não publicado`
          : metric === 'count'
            ? `${formatMetric(selectedValue, metric)} ${eventLabel} registrados em ${selectedMunicipality.name}`
            : `${formatMetric(selectedValue, metric)} ${eventLabel} por 100 mil habitantes em ${selectedMunicipality.name}`,
        comparison: selectedMunicipalValue.suppressed
          ? 'Célula pequena protegida pela regra de supressão'
          : metric === 'count'
            ? 'Contagem de eventos; use a taxa para comparar territórios'
            : difference === null
              ? 'Comparação estadual indisponível'
              : `${relativeDifferenceLabel(difference)} do restante do RJ`,
        detail: selectedMunicipalValue.suppressed
          ? 'O número não é zero. A contagem foi ocultada para proteger células pequenas.'
          : `RJ sem ${selectedMunicipality.name}: ${formatMetric(metric === 'count' ? restOfState?.count ?? null : restOfState?.value ?? null, metric)} · Brasil: ${formatMetric(metric === 'count' ? brazil?.count ?? null : brazil?.value ?? null, metric)}`,
      }
    }
    return null
  }, [indicator.measure, metric, municipalPeriod, observations, selectedMunicipality, selectedMunicipalValue])
  const provisional = observations?.some((item) => Number(item.period) >= startYear && Number(item.period) <= endYear && item.dataStatus === 'provisional') ?? false
  const stateTotalAtMunicipalPeriod = observations?.find((item) => item.geographyId === 'rj_total' && item.period === municipalPeriod && item.metricKind === metric) ?? null
  const brazilAtMunicipalPeriod = observations?.find((item) => item.geographyId === 'brazil_total' && item.period === municipalPeriod && item.metricKind === metric) ?? null
  const restOfState = restOfStateExcludingMunicipality(selectedMunicipalValue, stateTotalAtMunicipalPeriod)
  const stateRatio = rateRatio(selectedMunicipalValue?.value, restOfState?.value)
  const brazilRatio = rateRatio(selectedMunicipalValue?.value, brazilAtMunicipalPeriod?.value)
  const municipalChartObservations = useMemo(
    () => observations && municipalObservations && selectedMunicipalityCode
      ? buildMunicipalComparisonSeries(selectedMunicipalityCode, municipalObservations, observations)
      : [],
    [municipalObservations, observations, selectedMunicipalityCode],
  )
  const municipalChartGeographies = ['selected_municipality', 'rest_of_rj_excluding_selected', 'brazil_total']
  const municipalChartLabels = {
    ...catalog.geographies,
    selected_municipality: selectedMunicipality?.name ?? 'Município selecionado',
    rest_of_rj_excluding_selected: `RJ sem ${selectedMunicipality?.name ?? 'o município selecionado'}`,
  }
  const downloadFiltered = () => {
    if (!observations) return
    const csv = buildFilteredSeriesCsv(observations, {
      indicatorId: indicator.id,
      metric,
      geographies: activeGeographies,
      startYear,
      endYear,
    })
    saveCsvFile(`observatorio-${indicator.id}-${startYear}-${endYear}.csv`, csv)
  }
  return (
    <main className="explorer-page">
      <div className="explorer-title-row">
        <div><h1>Explorador de dados</h1><p>Compare territórios sem perder de vista fonte, unidade e grau de certeza.</p></div>
        <div className="explorer-title-actions">
          <ShareButton className="share-analysis" label="Compartilhar análise" surface="explorer" context={{ municipalityCode: selectedMunicipalityCode || undefined, indicatorId: indicator.id, period: `${startYear}-${endYear}`, metricKind: metric, template: activeTab === 'map' ? 'map' : 'evolution', format: 'og', route: 'explorer' }} />
          <span className="beta-status">{release.status === 'public_release_ready' ? 'Release aprovada' : 'Beta técnica'} · {release.releaseId}</span>
        </div>
      </div>
      <MunicipalityPicker municipalities={municipalities} selectedCode={selectedMunicipalityCode} onSelect={selectMunicipality} />
      <IndicatorFinder indicators={catalog.indicators} onSelect={onIndicator} />
      <ExplorerFilters
        theme={theme}
        indicators={catalog.indicators}
        indicatorId={indicator.id}
        metric={metric}
        startYear={startYear}
        endYear={endYear}
        onTheme={onTheme}
        onIndicator={onIndicator}
        onMetric={(value) => update({ medida: value })}
        onStartYear={(value) => update({ inicio: value })}
        onEndYear={(value) => update({ fim: value })}
        onDownload={downloadFiltered}
      />
      <section className="selection-summary" aria-label="Resumo da consulta atual">
        <div><span>Indicador</span><strong>{indicator.measureLabel}: {indicator.label}</strong></div>
        <div><span>Cidade escolhida</span><strong>{selectedMunicipality ? `${selectedMunicipality.name} · restante do RJ · Brasil` : 'Escolha uma cidade para comparar'}</strong></div>
        <div><span>Período</span><strong>{startYear}–{endYear}</strong></div>
        <Link href={`/indicadores/${indicator.id}`}>Entenda este indicador <ArrowRight /></Link>
      </section>
      {quickReading ? (
        <section className={`quick-reading${metric === 'count' ? ' quick-reading--warning' : ''}`} aria-labelledby="quick-reading-title">
          <div className="quick-reading__label">
            <span>Leitura rápida</span>
            <small>Dado do mapa municipal · {quickReading.year}</small>
          </div>
          <div className="quick-reading__main">
            <h2 id="quick-reading-title">{quickReading.headline}</h2>
            <strong>{quickReading.comparison}</strong>
          </div>
          <p>{quickReading.detail}</p>
          {metric === 'count' ? <button type="button" onClick={() => update({ medida: 'crude_rate_per_100k' })}>Comparar por taxa <ArrowRight /></button> : null}
        </section>
      ) : null}
      <div className="mobile-view-tabs" role="tablist" aria-label="Visualização principal">
        <button role="tab" aria-selected={activeTab === 'map'} className={activeTab === 'map' ? 'is-active' : ''} onClick={() => { setActiveTab('map'); trackEvent('map_series_toggled', { tab: 'map' }) }}>Mapa</button>
        <button role="tab" aria-selected={activeTab === 'series'} className={activeTab === 'series' ? 'is-active' : ''} onClick={() => { setActiveTab('series'); trackEvent('map_series_toggled', { tab: 'series' }) }}>Série temporal</button>
      </div>
      {activeTab === 'map' && availableMapPeriods.length > 1 && selectedMunicipality ? (
        <nav className="map-period-control" aria-label="Escolher ano do mapa municipal">
          <div><span>Ano do mapa</span><small>Compare a distribuição entre cidades</small></div>
          <div>
            {[...availableMapPeriods].reverse().map((period) => (
              <button key={period} type="button" aria-pressed={municipalPeriod === period} onClick={() => selectMapPeriod(period)}>{period}</button>
            ))}
          </div>
        </nav>
      ) : null}
      {observations ? (
        <>
          {activeTab === 'map' ? <section className="explorer-map-row">
            <TerritoryMap topology={topology} values={mapValues} scaleDomain={mapPayload?.scaleDomain} status={mapPayload?.status} period={municipalPeriod ?? undefined} selectedCode={selectedMunicipalityCode} onSelect={selectMunicipality} />
            <aside className="comparison-panel">
              {selectedMunicipality ? <>
                <h2>Comparação municipal</h2>
                <p>{municipalPeriod ?? 'Período disponível'} · {metricLabel(metric)}</p>
                <div className="comparison-list">
                  <div className={!selectedMunicipalValue || selectedMunicipalValue.suppressed ? 'is-unavailable' : ''}>
                    <span><i data-geography="selected_municipality" />{selectedMunicipality.name}</span>
                    <strong>{selectedMunicipalValue?.suppressed ? 'Não publicado' : formatMetric(metric === 'count' ? selectedMunicipalValue?.count ?? null : selectedMunicipalValue?.value ?? null, metric)}</strong>
                  </div>
                  <div className={!restOfState ? 'is-unavailable' : ''}>
                    <span><i data-geography="rest_of_rj_excluding_selected" />RJ sem {selectedMunicipality.name}</span>
                    <strong>{restOfState ? formatMetric(metric === 'count' ? restOfState.count : restOfState.value, metric) : 'Não disponível'}</strong>
                  </div>
                  <div className={!brazilAtMunicipalPeriod ? 'is-unavailable' : ''}>
                    <span><i data-geography="brazil_total" />Brasil</span>
                    <strong>{formatMetric(metric === 'count' ? brazilAtMunicipalPeriod?.count ?? null : brazilAtMunicipalPeriod?.value ?? null, metric)}</strong>
                  </div>
                </div>
                <div className="comparison-explain"><Info /><p>As taxas usam contagens e populações agregadas do território, não a média simples dos municípios.</p></div>
                <StatusNotice provisional={provisional} source={indicator.source} />
              </> : <div className="comparison-empty">
                <MapPin />
                <h2>Escolha uma cidade</h2>
                <p>Busque pelo nome acima ou clique diretamente no mapa para abrir dados, comparação e série histórica.</p>
                <a href="#municipality-input">Buscar uma cidade <ArrowRight /></a>
              </div>}
            </aside>
          </section> : null}
          {activeTab === 'map' && mapValues.length > 0 && selectedMunicipality ? (
            <>
              <section className="municipal-detail" aria-labelledby="municipal-detail-title">
                <div className="municipal-detail__heading">
                  <p className="eyebrow">Ficha municipal · snapshot {municipalPeriod}</p>
                  <h2 id="municipal-detail-title">{selectedMunicipality.name}</h2>
                  <p>Município de residência · {indicator.measureLabel.toLowerCase()}. Valores referentes ao período municipal selecionado: {municipalPeriod}.</p>
                </div>
                <div className="municipal-metrics">
                  <div><span>{indicator.measureLabel}</span><strong>{selectedMunicipalValue?.suppressed ? 'Não publicado' : formatMetric(selectedMunicipalValue?.count ?? null, 'count')}</strong><small>número bruto</small></div>
                  <div><span>Taxa bruta</span><strong>{selectedMunicipalValue?.suppressed ? 'Não publicado' : formatMetric(selectedMunicipalValue?.value ?? null, 'crude_rate_per_100k')}</strong><small>por 100 mil habitantes</small></div>
                  <div><span>Comparado ao restante do RJ</span><strong>{relativeDifferenceLabel(stateRatio)}</strong><small>{restOfState ? `${formatMetric(restOfState.value, 'crude_rate_per_100k')} no RJ sem a cidade` : 'indisponível com célula suprimida'}</small></div>
                  <div><span>Comparado ao Brasil</span><strong>{relativeDifferenceLabel(brazilRatio)}</strong><small>{brazilAtMunicipalPeriod ? `${formatMetric(brazilAtMunicipalPeriod.value, 'crude_rate_per_100k')} no Brasil` : 'quando a fonte é equivalente'}</small></div>
                </div>
              </section>
              <MunicipalTable municipalities={municipalities} values={mapValues} measureLabel={indicator.measureLabel} selectedCode={selectedMunicipalityCode} onSelect={selectMunicipality} />
            </>
          ) : null}
          {activeTab === 'series' && selectedMunicipality ? <section className="explorer-series is-mobile-primary">
            <SeriesInsights municipalityName={selectedMunicipality.name} observations={municipalChartObservations} />
            <div className="series-scope-note"><Info /><p><strong>Cobertura municipal validada:</strong> {municipalChartObservations.length ? [...new Set(municipalChartObservations.map((item) => item.period))].join(', ') : 'em preparação'}. Anos ausentes permanecem como lacunas e não são interpolados.</p></div>
            <TimeSeriesChart
              indicator={indicator}
              observations={municipalChartObservations}
              metric={metric}
              geographyLabels={municipalChartLabels}
              startYear={startYear}
              endYear={endYear}
              geographies={municipalChartGeographies}
            />
          </section> : activeTab === 'series' ? <section className="explorer-series-empty"><MapPin /><h2>Escolha uma cidade para ver a evolução</h2><p>A série municipal será carregada somente depois da seleção.</p><a href="#municipality-input">Escolher cidade</a></section> : null}
          <details className="indicator-definition">
            <summary><FileText />O que este indicador mostra?<ChevronDown /></summary>
            <div>
              <p>{indicator.definition}</p>
              <dl><div><dt>Fonte</dt><dd>{indicator.sourceLabel}</dd></div><div><dt>Status</dt><dd>{statusLabel(observations.at(-1)?.dataStatus ?? '')}</dd></div><div><dt>CID-10</dt><dd>{indicator.cidRanges.join(', ') || 'Definição própria da fonte'}</dd></div></dl>
              <Link href={`/indicadores/${indicator.id}`}>Ver fonte, método e limitações</Link>
            </div>
          </details>
        </>
      ) : <LoadingState label="Carregando série selecionada…" />}
    </main>
  )
}
