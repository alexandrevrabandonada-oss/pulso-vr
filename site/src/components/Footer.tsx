import { Link } from 'wouter'
import { CoBrandBlock } from './CoBrandBlock'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <CoBrandBlock />
        <div className="site-footer__trust"><strong>Dados públicos. Método transparente.</strong><p>Dados por residência · Release em preview · Sem inferência causal</p></div>
        <nav aria-label="Navegação do rodapé"><Link href="/metodos">Fontes e métodos</Link><Link href="/dados">Dados abertos</Link></nav>
      </div>
    </footer>
  )
}
