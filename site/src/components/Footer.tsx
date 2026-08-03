import { Link } from 'wouter'
import { BrandMark } from './BrandMark'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <BrandMark />
        <p>Dados por residência · Beta técnica · Sem inferência causal</p>
        <nav aria-label="Navegação do rodapé">
          <Link href="/metodos">Metodologia</Link>
          <Link href="/dados">Dados abertos</Link>
        </nav>
      </div>
    </footer>
  )
}
