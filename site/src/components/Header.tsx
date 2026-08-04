import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'wouter'
import { BrandMark } from './BrandMark'
import { CoBrandBlock } from './CoBrandBlock'

const links = [
  ['/', 'Início'],
  ['/explorador', 'Explorador de dados'],
  ['/perfis', 'Perfis'],
  ['/metodos', 'Fontes e métodos'],
  ['/dados', 'Dados abertos'],
] as const

export function Header() {
  const [open, setOpen] = useState(false)
  const [location] = useLocation()
  return (
    <header className="site-header glass-surface">
      <div className="site-header__inner">
        <Link href="/" className="brand-link" onClick={() => setOpen(false)}>
          <BrandMark />
        </Link>
        <div className="site-header__co-brand"><CoBrandBlock variant="header" /></div>
        <button
          className="menu-button"
          type="button"
          aria-label={open ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X /> : <Menu />}
          <span>Menu</span>
        </button>
        <nav className={`main-nav${open ? ' main-nav--open' : ''}`} aria-label="Navegação principal">
          {links.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={(href === '/' ? location === '/' : location.startsWith(href)) ? 'main-nav__link is-active' : 'main-nav__link'}
            >
              {label}
            </Link>
          ))}
          <div className="main-nav__partner"><CoBrandBlock variant="header" /></div>
        </nav>
      </div>
    </header>
  )
}
