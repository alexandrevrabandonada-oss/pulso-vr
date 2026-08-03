import { ArrowLeft } from 'lucide-react'
import { Link } from 'wouter'

export function NotFoundPage() {
  return (
    <main className="content-page not-found-page">
      <header className="content-page__header">
        <p>Página não encontrada</p>
        <h1>Este endereço não faz parte do portal</h1>
        <span>Use a navegação principal ou retorne ao explorador de dados.</span>
      </header>
      <Link className="primary-button" href="/explorador"><ArrowLeft />Voltar ao explorador</Link>
    </main>
  )
}
