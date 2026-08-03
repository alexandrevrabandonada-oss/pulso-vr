import type { MapFeatureProperties } from '../types'

export function municipalProperties(topology: unknown): MapFeatureProperties[] {
  const typed = topology as { objects?: { municipalities?: { geometries?: Array<{ properties?: MapFeatureProperties }> } } }
  return (typed.objects?.municipalities?.geometries ?? [])
    .map((geometry) => geometry.properties)
    .filter((properties): properties is MapFeatureProperties => Boolean(properties))
}

export function normalizeMunicipalityName(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim()
}

export function findMunicipality(query: string, municipalities: MapFeatureProperties[]) {
  const target = normalizeMunicipalityName(query)
  if (!target) return null
  return municipalities.find((item) => normalizeMunicipalityName(item.name) === target)
    ?? municipalities.find((item) => normalizeMunicipalityName(item.name).startsWith(target))
    ?? municipalities.find((item) => normalizeMunicipalityName(item.name).includes(target))
    ?? null
}
