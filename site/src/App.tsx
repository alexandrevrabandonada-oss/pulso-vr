import { Route, Switch } from 'wouter'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { PortalProvider } from './context/PortalContext'
import { DataPage } from './routes/DataPage'
import { ExplorerPage } from './routes/ExplorerPage'
import { HomePage } from './routes/HomePage'
import { IndicatorPage } from './routes/IndicatorPage'
import { MethodsPage } from './routes/MethodsPage'
import { NotFoundPage } from './routes/NotFoundPage'
import { ProfilesPage } from './routes/ProfilesPage'

export function App() {
  return (
    <>
      <Header />
      <PortalProvider>
        <Switch>
          <Route path="/" component={HomePage} />
          <Route path="/explorador" component={ExplorerPage} />
          <Route path="/indicadores/:id" component={IndicatorPage} />
          <Route path="/perfis" component={ProfilesPage} />
          <Route path="/metodos" component={MethodsPage} />
          <Route path="/dados" component={DataPage} />
          <Route><NotFoundPage /></Route>
        </Switch>
      </PortalProvider>
      <Footer />
    </>
  )
}
