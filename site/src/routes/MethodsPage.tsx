import { usePortal } from '../context/usePortal'

export function MethodsPage() {
  const { release } = usePortal()
  return (
    <main className="content-page methods-page">
      <header className="content-page__header"><p>Transparência</p><h1>Fontes e métodos</h1><span>Como os dados são adquiridos, comparados e preparados para publicação.</span></header>
      <section><h2>Quatro regras para ler o portal</h2><ol className="numbered-methods"><li><strong>Residência define o território.</strong><span>Local de atendimento ou ocorrência nunca substitui o município de residência.</span></li><li><strong>Eventos não são pessoas.</strong><span>Uma AIH registra uma internação; uma mesma pessoa pode aparecer mais de uma vez.</span></li><li><strong>Mortalidade não é incidência.</strong><span>O SIM informa óbitos pela causa básica. RHC e registros assistenciais também não são incidência populacional.</span></li><li><strong>Associação não prova causa.</strong><span>Comparações ecológicas não autorizam atribuir efeitos à CSN ou a qualquer fonte específica.</span></li></ol></section>
      <section className="method-columns"><div><h2>Comparadores</h2><p>O comparador principal agrega contagens e população de todo o RJ, excluindo Volta Redonda. Brasil é secundário e só aparece quando numerador e denominador nacionais estão validados.</p></div><div><h2>Taxas</h2><p>A interface nomeia taxas brutas explicitamente. Taxas padronizadas só serão oferecidas quando usarem o mesmo padrão etário e denominadores compatíveis.</p></div><div><h2>Supressão</h2><p>Células com contagem menor que {release.smallCellThreshold} são removidas antes da publicação. O navegador nunca recebe seus números.</p></div></section>
      <section><h2>Marcos temporais</h2><div className="timeline-method"><div><time>mar/2020</time><p>Ruptura respiratória da pandemia.</p></div><div><time>2020–2022</time><p>Interrupção assistencial relevante para câncer.</p></div><div><time>mar/2022</time><p>Início da Linha de Atenção Oncológica.</p></div><div><time>2025+</time><p>Período provisório influenciado pela expansão do Prevenir 50+.</p></div></div></section>
    </main>
  )
}
