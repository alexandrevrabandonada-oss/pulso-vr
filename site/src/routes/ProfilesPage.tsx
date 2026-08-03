import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearch } from 'wouter'
import { LoadingState } from '../components/LoadingState'
import { usePortal } from '../context/usePortal'
import { trackEvent } from '../lib/analytics'
import { loadProfile } from '../lib/data'
import { formatMetric } from '../lib/format'
import { municipalProperties } from '../lib/municipalities'
import type { ProfileObservation } from '../types'

const AGE_ORDER = ['<1', '1-4', '5-14', '15-24', '25-44', '45-64', '65-74', '75+']

function safeParameter(value: string | null, allowed: Set<string>, fallback: string) {
  return value && allowed.has(value) ? value : fallback
}

function profileValueLabel(observation: ProfileObservation | null, compact = false) {
  if (observation?.suppressionStatus === 'published') return formatMetric(observation.ratePer100k, 'crude_rate_per_100k')
  if (observation?.suppressionStatus === 'not_applicable') return 'Não aplicável'
  return compact ? 'Protegido' : 'Célula protegida'
}

export function ProfilesPage() {
  const { catalog, topology } = usePortal()
  const search = useSearch()
  const [, navigate] = useLocation()
  const parameters = useMemo(() => new URLSearchParams(search), [search])
  const municipalities = useMemo(() => municipalProperties(topology), [topology])
  const available = catalog.indicators.filter((item) => item.profileCoverage?.status === 'available')
  const municipalityCodes = useMemo(() => new Set(municipalities.map((item) => item.code)), [municipalities])
  const indicatorIds = useMemo(() => new Set(available.map((item) => item.id)), [available])
  const defaultMunicipality = ''
  const defaultIndicator = available.find((item) => item.outcomeId === 'all_malignant_neoplasms')?.id ?? available[0]?.id ?? ''
  const municipalityCode = safeParameter(parameters.get('municipio'), municipalityCodes, defaultMunicipality)
  const indicatorId = safeParameter(parameters.get('indicador'), indicatorIds, defaultIndicator)
  const period = parameters.get('periodo') === '2022' ? '2022' : '2022'
  const municipality = municipalities.find((item) => item.code === municipalityCode)
  const indicator = available.find((item) => item.id === indicatorId)
  const [rows, setRows] = useState<ProfileObservation[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!indicatorId || !municipalityCode) { setRows([]); return }
    let active = true
    setRows(null)
    setFailed(false)
    loadProfile(indicatorId, period)
      .then((payload) => { if (active) setRows(payload.observations) })
      .catch(() => {
        if (active) { setRows([]); setFailed(true) }
        trackEvent('data_load_error', { surface: 'profiles' })
      })
    return () => { active = false }
  }, [indicatorId, municipalityCode, period])

  const profile = useMemo(() => {
    const selected = (rows ?? []).filter((row) => row.municipalityCode === municipalityCode && row.period === period)
    return AGE_ORDER.map((age) => ({
      age,
      feminino: selected.find((row) => row.ageGroup === age && row.sex === 'feminino') ?? null,
      masculino: selected.find((row) => row.ageGroup === age && row.sex === 'masculino') ?? null,
    }))
  }, [municipalityCode, period, rows])
  const max = Math.max(...profile.flatMap((item) => [item.feminino?.ratePer100k ?? 0, item.masculino?.ratePer100k ?? 0]), 1)
  const setSelection = (nextMunicipality = municipalityCode, nextIndicator = indicatorId) => {
    navigate(`/perfis?municipio=${nextMunicipality}&indicador=${nextIndicator}&periodo=${period}`, { replace: true })
  }

  if (!available.length) {
    return <main className="content-page profiles-page"><header className="content-page__header"><h1>Perfis por idade e sexo</h1><span>Os perfis municipais ainda não estão disponíveis nesta release.</span></header><Link href="/">Escolher outro assunto</Link></main>
  }

  return (
    <main className="content-page profiles-page">
      <header className="content-page__header"><h1>Perfis por idade e sexo</h1><span>Taxas específicas de mortalidade de residentes em 2022. Estes valores não são taxas padronizadas.</span></header>
      <section className="profile-controls" aria-label="Selecionar perfil">
        <label>Município<select value={municipalityCode} onChange={(event) => setSelection(event.target.value)}><option value="" disabled>Escolha um município</option>{municipalities.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
        <label>Indicador<select value={indicatorId} onChange={(event) => setSelection(municipalityCode, event.target.value)}>{available.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <label>Período<select value={period} disabled><option value="2022">2022</option></select></label>
      </section>
      {!municipalityCode ? <section className="profile-empty"><h2>Escolha uma cidade para começar</h2><p>O perfil será carregado somente depois da seleção, sem adotar um município silenciosamente.</p></section> : rows ? (
        failed ? <section className="profile-empty" role="alert"><h2>Não foi possível carregar o perfil</h2><p>Tente novamente ou consulte a análise municipal sem o recorte por idade e sexo.</p></section> :
        <section className="profile-chart" aria-labelledby="profile-title">
          <div className="profile-chart__heading"><div><h2 id="profile-title">{indicator?.label}</h2><p>{municipality?.name} · 2022 · taxa específica por 100 mil</p></div><div className="profile-legend"><span><i />Feminino</span><span><i />Masculino</span></div></div>
          <div className="profile-bars" aria-hidden="true">
            {profile.map((item) => (
              <div className="profile-row" key={item.age}>
                <strong>{item.age}</strong>
                {[item.feminino, item.masculino].map((observation, index) => <div key={index}><span className={`profile-bar ${index === 0 ? 'profile-bar--female' : 'profile-bar--male'}`} style={{ width: `${((observation?.ratePer100k ?? 0) / max) * 100}%` }} /><em>{profileValueLabel(observation, true)}</em></div>)}
              </div>
            ))}
          </div>
          <div className="profile-table-wrap"><table><caption>Alternativa tabular do perfil por idade e sexo</caption><thead><tr><th>Idade</th><th>Feminino</th><th>Masculino</th></tr></thead><tbody>{profile.map((item) => <tr key={item.age}><th>{item.age}</th><td>{profileValueLabel(item.feminino)}</td><td>{profileValueLabel(item.masculino)}</td></tr>)}</tbody></table></div>
          <p className="profile-note">Células protegidas não representam zero. Idade ou sexo ignorado não recebe denominador inventado. Mortalidade por câncer não representa incidência.</p>
        </section>
      ) : <LoadingState label={`Carregando perfil de ${municipality?.name ?? 'município'}…`} />}
    </main>
  )
}
