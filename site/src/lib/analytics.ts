const ALLOWED_EVENTS = new Set([
  'discovery_search', 'municipality_opened', 'indicator_selected', 'filters_opened',
  'map_series_toggled', 'download_completed', 'share_opened', 'share_template_selected', 'share_completed', 'share_failed', 'data_load_error',
  'first_answer_rendered', 'interpretation_opened', 'profile_opened',
])

export function trackEvent(name: string, properties: Record<string, string | number | boolean> = {}) {
  if (!ALLOWED_EVENTS.has(name)) return
  const detail = { schemaVersion: '1.0.0', name, properties, path: window.location.pathname, at: new Date().toISOString(), retentionDays: 90 }
  window.dispatchEvent(new CustomEvent('observatorio:analytics', { detail }))
  const endpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT
  if (endpoint) navigator.sendBeacon(endpoint, JSON.stringify(detail))
}
