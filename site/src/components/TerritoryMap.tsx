import { geoIdentity, geoPath } from 'd3-geo'
import { MapPin } from 'lucide-react'
import { useMemo, useState } from 'react'
import { feature } from 'topojson-client'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import type { MapFeatureProperties, MapValue } from '../types'

interface TopologyLike {
  objects: { municipalities: unknown }
}

interface TerritoryMapProps {
  topology: unknown
  compact?: boolean
  values?: MapValue[]
  status?: string
  period?: string
  selectedCode?: string | null
  onSelect?: (code: string) => void
  scaleDomain?: [number, number] | null
}

export function TerritoryMap({ topology, compact = false, values = [], status = '', period, selectedCode = null, onSelect, scaleDomain = null }: TerritoryMapProps) {
  const [focused, setFocused] = useState<MapFeatureProperties | null>(null)
  const valuesByCode = useMemo(() => new Map(values.map((value) => [value.geographyId, value])), [values])
  const isSihMap = status.startsWith('validated_sih_')
  const hasPublishedMap = status.startsWith('validated_')
  const valueRange = useMemo(() => {
    const published = values.map((value) => value.value).filter((value): value is number => value !== null)
    if (scaleDomain) return { min: scaleDomain[0], max: scaleDomain[1] }
    return published.length ? { min: Math.min(...published), max: Math.max(...published) } : null
  }, [scaleDomain, values])
  const mapColor = (value: number | null | undefined) => {
    if (value === null || value === undefined || !valueRange) return undefined
    const span = valueRange.max - valueRange.min
    const intensity = span === 0 ? 0.5 : (value - valueRange.min) / span
    return `hsl(49 100% ${Math.round(88 - intensity * 48)}%)`
  }
  const { features, paths } = useMemo(() => {
    const topologyValue = topology as TopologyLike
    const collection = feature(
      topology as never,
      topologyValue.objects.municipalities as never,
    ) as unknown as FeatureCollection<Geometry, MapFeatureProperties>
    const projection = geoIdentity().reflectY(true).fitExtent(
      compact ? [[18, 16], [482, 265]] : [[38, 24], [862, 430]],
      collection,
    )
    const path = geoPath(projection)
    return {
      features: collection.features,
      paths: collection.features.map((item) => path(item as Feature) ?? ''),
    }
  }, [topology, compact])

  const selected = focused ?? features.find((item) => item.properties.code === selectedCode)?.properties ?? null
  return (
    <div className={`territory-map${compact ? ' territory-map--compact' : ''}`}>
      <div className="territory-map__canvas">
        <svg viewBox={compact ? '0 0 500 285' : '0 0 900 460'} role="img" aria-labelledby="map-title map-desc">
          <title id="map-title">Mapa dos municípios do Estado do Rio de Janeiro</title>
          <desc id="map-desc">O município selecionado está destacado. {hasPublishedMap ? `Valores municipais ${isSihMap ? 'de internações SIH' : 'de mortalidade SIM'} estão disponíveis no período indicado; células pequenas são suprimidas.` : 'A malha é usada como contexto territorial e não representa taxas municipais ainda não validadas.'}</desc>
          <rect width="100%" height="100%" className="map-ocean" />
          <g>
            {features.map((item, index) => {
              const mapValue = valuesByCode.get(item.properties.code)
              const hasPublishedValue = mapValue?.value !== null && mapValue?.value !== undefined
              const isSelected = selectedCode === item.properties.code
              const isAccessible = Boolean(onSelect)
              return (
                <path
                  key={item.properties.code}
                  d={paths[index]}
                  className={`map-municipality${hasPublishedValue ? ' map-municipality--has-data' : ''}${isSelected ? ' map-municipality--selected' : ''}`}
                  style={hasPublishedValue ? { fill: mapColor(mapValue?.value) } : undefined}
                  tabIndex={isAccessible ? 0 : -1}
                  aria-hidden={isAccessible ? undefined : true}
                  aria-label={`${item.properties.name}${isSelected ? ', município selecionado' : ''}${hasPublishedValue ? `, taxa ${mapValue.value?.toFixed(1)} por 100 mil em ${mapValue.period}` : ''}`}
                  onMouseEnter={() => setFocused(item.properties)}
                  onMouseLeave={() => setFocused(null)}
                  onFocus={() => setFocused(item.properties)}
                  onBlur={() => setFocused(null)}
                  onClick={() => onSelect?.(item.properties.code)}
                />
              )
            })}
          </g>
        </svg>
        <div className="map-legend" aria-hidden="true">
          <span><i className="map-legend__selected" />Município selecionado</span>
          {hasPublishedMap ? <><span><i className="map-legend__scale map-legend__scale--low" />{valueRange?.min.toFixed(1) ?? 'Menor taxa'}</span><span><i className="map-legend__scale map-legend__scale--high" />{valueRange?.max.toFixed(1) ?? 'Maior taxa'}</span></> : <span><i />92 municípios do RJ</span>}
        </div>
        {selected ? (
          <div className="map-tooltip" aria-live="polite">
            <MapPin size={16} />
            <span>{selected.name}{valuesByCode.get(selected.code)?.value !== null && valuesByCode.get(selected.code)?.value !== undefined ? ` · ${valuesByCode.get(selected.code)?.value?.toFixed(1)} / 100 mil` : ''}</span>
          </div>
        ) : null}
      </div>
      <div className="territory-map__note">
        <strong>{hasPublishedMap ? `Mapa municipal · ${isSihMap ? 'SIH' : 'SIM'} ${period ?? values[0]?.period ?? ''}` : 'Mapa contextual'}</strong>
        <span>{hasPublishedMap ? `${isSihMap ? 'Taxa bruta de internações por residência; AIHs são eventos' : 'Taxa bruta de mortalidade por residência'}; células menores que cinco estão suprimidas. A escala é fixa para os períodos disponíveis deste indicador.` : 'Malha dos 92 municípios; nenhuma cidade é usada como referência padrão.'}</span>
      </div>
    </div>
  )
}
