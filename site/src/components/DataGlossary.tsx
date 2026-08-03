import { BookOpen } from 'lucide-react'
import { trackEvent } from '../lib/analytics'

const TERMS = [
  ['Taxa por 100 mil', 'Permite comparar populações de tamanhos diferentes. Nesta página, a taxa é bruta e não foi padronizada por idade.'],
  ['RJ sem esta cidade', 'Soma os eventos e a população do estado depois de retirar o município selecionado. Não é uma média simples das cidades.'],
  ['Dado protegido', 'Uma contagem pequena foi ocultada antes da publicação. O valor ausente não representa zero.'],
  ['Provisório', 'O período ainda pode ser revisto pela fonte e deve ser interpretado separadamente dos anos definitivos.'],
] as const

export function DataGlossary() {
  return (
    <details className="data-glossary" onToggle={(event) => {
      if (event.currentTarget.open) trackEvent('interpretation_opened', { surface: 'municipality_glossary' })
    }}>
      <summary><BookOpen aria-hidden="true" />Palavras importantes para ler esta página</summary>
      <dl>{TERMS.map(([term, definition]) => <div key={term}><dt>{term}</dt><dd>{definition}</dd></div>)}</dl>
    </details>
  )
}
