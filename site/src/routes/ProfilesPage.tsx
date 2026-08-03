import { useEffect, useMemo, useState } from 'react'
import { useLocation, useSearch } from 'wouter'
import { usePortal } from '../context/usePortal'
import { loadProfile } from '../lib/data'
import { formatMetric } from '../lib/format'
import type { ProfileObservation } from '../types'
import { LoadingState } from '../components/LoadingState'

const AGE_ORDER = ['<1', '1-4', '5-14', '15-24', '25-44', '45-64', '65-74', '75+']

export function ProfilesPage() {
  const { catalog } = usePortal()
  const search = useSearch()
  const [, navigate] = useLocation()
  const available = catalog.indicators.filter((item) => item.source === 'SIM')
  const requested = new URLSearchParams(search).get('indicador')
  const [indicatorId, setIndicatorId] = useState(available.some((item) => item.id === requested) ? requested! : available.find((item) => item.outcomeId === 'all_malignant_neoplasms')?.id ?? available[0].id)
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
      <header className="content-page__header"><p>Piloto de cobertura limitada</p><h1>Perfis por idade e sexo</h1><span>Esta página ainda não representa os 92 municípios. Nesta release, o recorte validado está disponível somente para Volta Redonda em 2022; a expansão municipal permanece bloqueada até validação de numeradores e denominadores.</span></header>
      <div className="profile-coverage-warning" role="status"><strong>Não use este piloto como perfil estadual.</strong><span>Células menores que cinco estão suprimidas e não representam zero.</span></div>
      <label className="profile-selector">Indicador<select value={indicatorId} onChange={(event) => { setIndicatorId(event.target.value); navigate(`/perfis?indicador=${event.target.value}`, { replace: true }) }}>{available.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      {rows ? (
        <section className="profile-chart" aria-labelledby="profile-title">
          <div className="profile-chart__heading"><div><h2 id="profile-title">{indicator.label}</h2><p>Recorte disponível: Volta Redonda · 2022 · taxa específica por 100 mil</p></div><div className="profile-legend"><span><i />Feminino</span><span><i />Masculino</span></div></div>
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
