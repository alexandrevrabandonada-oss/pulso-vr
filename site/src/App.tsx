import { lazy, Suspense } from 'react'
import { Route, Switch, useLocation } from 'wouter'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { LoadingState } from './components/LoadingState'
import { CoBrandBlock } from './components/CoBrandBlock'
import { PortalProvider } from './context/PortalContext'
import { HomePage } from './routes/HomePage'
import { SeoHead } from './components/SeoHead'

const DataPage = lazy(() => import('./routes/DataPage').then((module) => ({ default: module.DataPage })))
const ExplorerPage = lazy(() => import('./routes/ExplorerPage').then((module) => ({ default: module.ExplorerPage })))
const IndicatorPage = lazy(() => import('./routes/IndicatorPage').then((module) => ({ default: module.IndicatorPage })))
const MethodsPage = lazy(() => import('./routes/MethodsPage').then((module) => ({ default: module.MethodsPage })))
const MunicipalityPage = lazy(() => import('./routes/MunicipalityPage').then((module) => ({ default: module.MunicipalityPage })))
const NotFoundPage = lazy(() => import('./routes/NotFoundPage').then((module) => ({ default: module.NotFoundPage })))
const ProfilesPage = lazy(() => import('./routes/ProfilesPage').then((module) => ({ default: module.ProfilesPage })))

export function App() {
  return (
    <>
      <Header />
      <PortalProvider>
        <SeoHead />
        <Suspense fallback={<main className="content-page"><LoadingState label="Carregando página…" /></main>}>
          <RoutedContent />
        </Suspense>
      </PortalProvider>
      <Footer />
    </>
  )
}

function RoutedContent() {
  const [location] = useLocation()
  return <>
    <Switch>
      <Route path="/" component={HomePage} />
      <Route path="/explorador" component={ExplorerPage} />
      <Route path="/indicadores/:id" component={IndicatorPage} />
      <Route path="/municipios/:codigo" component={MunicipalityPage} />
      <Route path="/perfis" component={ProfilesPage} />
      <Route path="/metodos" component={MethodsPage} />
      <Route path="/dados" component={DataPage} />
      <Route><NotFoundPage /></Route>
    </Switch>
    {location !== '/' ? <div className="page-brand-credit"><CoBrandBlock variant="page" /></div> : null}
  </>
}
