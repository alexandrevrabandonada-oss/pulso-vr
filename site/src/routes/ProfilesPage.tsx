import { useEffect, useMemo, useState } from 'react'
import { usePortal } from '../context/usePortal'
import { loadProfile } from '../lib/data'
import { formatMetric } from '../lib/format'
import type { ProfileObservation } from '../types'
import { LoadingState } from '../components/LoadingState'

const AGE_ORDER = ['<1', '1-4', '5-14', '15-24', '25-44', '45-64', '65-74', '75+']

export function ProfilesPage() {
  const { catalog } = usePortal()
  const available = catalog.indicators.filter((item) => item.source === 'SIM')
  const [indicatorId, setIndicatorId] = useState(available.find((item) => item.outcomeId === 'all_malignant_neoplasms')?.id ?? available[0].id)
  const [rows, setRows] = useState<ProfileObservation[] | null>(null)
  useEffect(() => {
    setRows(null)
    loadProfile(indicatorId).then((payload) => setRows(payload.observations))
  }, [indicatorId])
  const indicator = available.find((item) => item.id === indicatorId)!
  const profile = useMemo(() => {
    if (!rows) return []
    return AGE_ORDER.map((age) => {
      const values = rows.filter((row) => row.ageGroup === age && row.geographyId === 'volta_redonda' && !row.suppressed)
      return {
        age,
        feminino: values.find((row) => row.sex === 'feminino')?.value ?? null,
        masculino: values.find((row) => row.sex === 'masculino')?.value ?? null,
      }
    })
  }, [rows])
  const max = Math.max(...profile.flatMap((item) => [item.feminino ?? 0, item.masculino ?? 0]), 1)
  return (
    <main className="content-page profiles-page">
      <header className="content-page__header"><p>População</p><h1>Perfis por idade e sexo</h1><span>Taxas específicas brutas do SIM para 2022; células menores que cinco estão suprimidas.</span></header>
      <label className="profile-selector">Indicador<select value={indicatorId} onChange={(event) => setIndicatorId(event.target.value)}>{available.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      {rows ? (
        <section className="profile-chart" aria-labelledby="profile-title">
          <div className="profile-chart__heading"><div><h2 id="profile-title">{indicator.label}</h2><p>Volta Redonda · 2022 · taxa específica por 100 mil</p></div><div className="profile-legend"><span><i />Feminino</span><span><i />Masculino</span></div></div>
          <div className="profile-bars">
            {profile.map((item) => (
              <div className="profile-row" key={item.age}>
                <strong>{item.age}</strong>
                <div><span className="profile-bar profile-bar--female" style={{ width: `${((item.feminino ?? 0) / max) * 100}%` }} /><em>{formatMetric(item.feminino, 'crude_rate_per_100k')}</em></div>
                <div><span className="profile-bar profile-bar--male" style={{ width: `${((item.masculino ?? 0) / max) * 100}%` }} /><em>{formatMetric(item.masculino, 'crude_rate_per_100k')}</em></div>
              </div>
            ))}
          </div>
          <p className="profile-note">Este recorte não substitui uma série padronizada por idade. Valores “—” podem representar célula suprimida ou ausência na fonte.</p>
        </section>
      ) : <LoadingState />}
    </main>
  )
}
