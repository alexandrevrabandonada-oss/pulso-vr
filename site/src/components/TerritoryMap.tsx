import { geoIdentity, geoPath } from 'd3-geo'
import { MapPin } from 'lucide-react'
import { useMemo, useState } from 'react'
import { feature } from 'topojson-client'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import type { MapFeatureProperties } from '../types'

interface TopologyLike {
  objects: { municipalities: unknown }
}

interface TerritoryMapProps {
  topology: unknown
  compact?: boolean
}

export function TerritoryMap({ topology, compact = false }: TerritoryMapProps) {
  const [focused, setFocused] = useState<MapFeatureProperties | null>(null)
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

  const selected = focused ?? features.find((item) => item.properties.isVoltaRedonda)?.properties ?? null
  return (
    <div className={`territory-map${compact ? ' territory-map--compact' : ''}`}>
      <div className="territory-map__canvas">
        <svg viewBox={compact ? '0 0 500 285' : '0 0 900 460'} role="img" aria-labelledby="map-title map-desc">
          <title id="map-title">Mapa dos municípios do Estado do Rio de Janeiro</title>
          <desc id="map-desc">Volta Redonda está destacada. A malha é usada como contexto territorial e não representa taxas municipais ainda não validadas.</desc>
          <rect width="100%" height="100%" className="map-ocean" />
          <g>
            {features.map((item, index) => {
              const isVr = item.properties.isVoltaRedonda
              return (
                <path
                  key={item.properties.code}
                  d={paths[index]}
                  className={isVr ? 'map-municipality map-municipality--vr' : 'map-municipality'}
                  tabIndex={isVr ? 0 : -1}
                  aria-hidden={isVr ? undefined : true}
                  aria-label={`${item.properties.name}${isVr ? ', Volta Redonda destacada' : ''}`}
                  onMouseEnter={() => setFocused(item.properties)}
                  onMouseLeave={() => setFocused(null)}
                  onFocus={() => setFocused(item.properties)}
                  onBlur={() => setFocused(null)}
                />
              )
            })}
          </g>
        </svg>
        <div className="map-legend" aria-hidden="true">
          <span><i className="map-legend__vr" />Volta Redonda</span>
          <span><i />Demais municípios do RJ</span>
        </div>
        {selected ? (
          <div className="map-tooltip" aria-live="polite">
            <MapPin size={16} />
            <span>{selected.name}</span>
          </div>
        ) : null}
      </div>
      <div className="territory-map__note">
        <strong>Mapa contextual</strong>
        <span>Taxas municipais serão ativadas somente após validação por residência.</span>
      </div>
    </div>
  )
}
