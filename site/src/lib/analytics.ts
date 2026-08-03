const ALLOWED_EVENTS = new Set([
  'discovery_search', 'municipality_opened', 'indicator_selected', 'filters_opened',
  'map_series_toggled', 'download_completed', 'share_completed', 'data_load_error',
])

export function trackEvent(name: string, properties: Record<string, string | number | boolean> = {}) {
  if (!ALLOWED_EVENTS.has(name)) return
  const detail = { name, properties, path: window.location.pathname, at: new Date().toISOString() }
  window.dispatchEvent(new CustomEvent('observatorio:analytics', { detail }))
  const endpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT
  if (endpoint) navigator.sendBeacon(endpoint, JSON.stringify(detail))
}
