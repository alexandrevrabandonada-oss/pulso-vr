import { BookOpen } from 'lucide-react'
import { trackEvent } from '../lib/analytics'

const TERMS = [
  ['Taxa bruta por 100 mil', 'Relaciona os eventos à população do território. Pode refletir diferenças na composição etária entre municípios.'],
  ['Taxa padronizada', 'Recalcula a comparação usando uma população-padrão. Nesta página, ela aparece separada da taxa bruta e sempre traz seu ano e dimensões.'],
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
