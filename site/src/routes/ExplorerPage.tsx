import { ChevronDown, FileText, Info } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearch } from 'wouter'
import { ExplorerFilters } from '../components/ExplorerFilters'
import { LoadingState } from '../components/LoadingState'
import { StatusNotice } from '../components/StatusNotice'
import { TerritoryMap } from '../components/TerritoryMap'
import { TimeSeriesChart } from '../components/TimeSeriesChart'
import { usePortal } from '../context/usePortal'
import { loadMap, loadSeries } from '../lib/data'
import { deriveExplorerState, explorerStateSearch } from '../lib/explorerState'
import { formatMetric, metricLabel, statusLabel } from '../lib/format'
import { buildFilteredSeriesCsv, saveCsvFile } from '../lib/publicDownload'
import type { Observation, Theme } from '../types'

const GEO_ORDER = ['volta_redonda', 'rest_of_rj_excluding_vr', 'brazil_total']

export function ExplorerPage() {
  const { catalog, release, topology } = usePortal()
  const [, navigate] = useLocation()
  const search = useSearch()
  const searchParams = useMemo(() => new URLSearchParams(search), [search])
  const explorerState = useMemo(
    () => deriveExplorerState(search, catalog.indicators),
    [search, catalog.indicators],
  )
  const { indicator, theme, metric, territory, startYear, endYear } = explorerState
  const [observations, setObservations] = useState<Observation[] | null>(null)
  const [mapPayload, setMapPayload] = useState<{ values: import('../types').MapValue[]; status: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'map' | 'series'>('map')
  const activeGeographies = territory === 'all' ? GEO_ORDER : GEO_ORDER.filter((id) => id === territory)

  useEffect(() => {
    const canonicalSearch = explorerStateSearch(explorerState)
    if (canonicalSearch !== search) navigate(`/explorador?${canonicalSearch}`, { replace: true })
  }, [explorerState, navigate, search])

  useEffect(() => {
    let active = true
    setObservations(null)
    setMapPayload(null)
    Promise.all([loadSeries(indicator.id), loadMap(indicator.id)]).then(([seriesPayload, nextMap]) => {
      if (active) {
        setObservations(seriesPayload.observations)
        setMapPayload({ values: nextMap.values, status: nextMap.status })
      }
    })
    return () => { active = false }
  }, [indicator.id])

  const update = (changes: Record<string, string | number>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => next.set(key, String(value)))
    navigate(`/explorador?${next.toString()}`, { replace: true })
  }
  const onTheme = (value: Theme) => {
    const nextIndicator = catalog.indicators.find((item) => item.theme === value)!
    navigate(`/explorador?${new URLSearchParams({
      tema: value,
      indicador: nextIndicator.id,
      medida: 'crude_rate_per_100k',
      territorio: 'all',
      inicio: String(nextIndicator.yearStart),
      fim: String(nextIndicator.yearEnd),
    }).toString()}`)
  }
  const onIndicator = (value: string) => {
    const nextIndicator = catalog.indicators.find((item) => item.id === value)!
    update({ indicador: value, tema: nextIndicator.theme, inicio: nextIndicator.yearStart, fim: nextIndicator.yearEnd })
  }

  const comparison = useMemo(() => {
    if (!observations) return []
    return GEO_ORDER.map((geographyId) => {
      const candidates = observations.filter((item) => item.geographyId === geographyId && Number(item.period) >= startYear && Number(item.period) <= endYear)
      const latest = [...candidates].sort((a, b) => Number(b.period) - Number(a.period)).find((item) => (metric === 'count' ? item.count : item.value) !== null)
      return { geographyId, latest }
    })
  }, [observations, startYear, endYear, metric])
  const provisional = observations?.some((item) => Number(item.period) >= startYear && Number(item.period) <= endYear && item.dataStatus === 'provisional') ?? false
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
        <span className="beta-status">{release.status === 'public_release_ready' ? 'Release aprovada' : 'Beta técnica'} · {release.releaseId}</span>
      </div>
      <ExplorerFilters
        theme={theme}
        indicators={catalog.indicators}
        indicatorId={indicator.id}
        territory={territory}
        metric={metric}
        startYear={startYear}
        endYear={endYear}
        onTheme={onTheme}
        onIndicator={onIndicator}
        onTerritory={(value) => update({ territorio: value })}
        onMetric={(value) => update({ medida: value })}
        onStartYear={(value) => update({ inicio: value })}
        onEndYear={(value) => update({ fim: value })}
        onDownload={downloadFiltered}
      />
      <div className="mobile-view-tabs" role="tablist" aria-label="Visualização principal">
        <button role="tab" aria-selected={activeTab === 'map'} className={activeTab === 'map' ? 'is-active' : ''} onClick={() => setActiveTab('map')}>Mapa</button>
        <button role="tab" aria-selected={activeTab === 'series'} className={activeTab === 'series' ? 'is-active' : ''} onClick={() => setActiveTab('series')}>Série temporal</button>
      </div>
      {observations ? (
        <>
          <section className={`explorer-map-row${activeTab === 'series' ? ' is-mobile-hidden' : ''}`}>
            <TerritoryMap topology={topology} values={mapPayload?.values} status={mapPayload?.status} />
            <aside className="comparison-panel">
              <h2>Comparação no período selecionado</h2>
              <p>{startYear} a {endYear} · {metricLabel(metric)}</p>
              <div className="comparison-list">
                {comparison.filter(({ geographyId }) => activeGeographies.includes(geographyId)).map(({ geographyId, latest }) => (
                  <div key={geographyId} className={!latest ? 'is-unavailable' : ''}>
                    <span><i data-geography={geographyId} />{catalog.geographies[geographyId]}</span>
                    {latest ? (
                      <strong>{formatMetric(metric === 'count' ? latest.count : latest.value, metric)} <small>em {latest.period}</small></strong>
                    ) : <strong>Em preparação</strong>}
                  </div>
                ))}
              </div>
              <div className="comparison-explain"><Info /><p>As taxas usam contagens e populações agregadas do território, não a média simples dos municípios.</p></div>
              <StatusNotice provisional={provisional} source={indicator.source} />
            </aside>
          </section>
          <section className={`explorer-series${activeTab === 'map' ? '' : ' is-mobile-primary'}`}>
            <TimeSeriesChart
              indicator={indicator}
              observations={observations}
              metric={metric}
              geographyLabels={catalog.geographies}
              startYear={startYear}
              endYear={endYear}
              geographies={activeGeographies}
            />
          </section>
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
