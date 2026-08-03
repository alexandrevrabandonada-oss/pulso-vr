# Revisão de acessibilidade — minuta de aprovação

Status: **approved_by_project_owner_technical_evidence**  
Data: 2026-08-03

Esta minuta reúne a verificação automatizada e manual realizada no portal beta
e a aprovação do responsável pelo projeto. Ela não representa auditoria externa
independente de acessibilidade.

## Verificações concluídas

- [x] Rotas principais carregam conteúdo sem tela vazia ou overlay de framework.
- [x] Navegação principal e rodapé usam links identificáveis.
- [x] Filtros têm labels acessíveis; controles de faixa etária e sexo indicam quando estão desabilitados.
- [x] Mapa tem título, descrição, regiões identificáveis e destaque de Volta Redonda.
- [x] Valores municipais publicados aparecem em rótulos acessíveis; células suprimidas não expõem contagem.
- [x] Série temporal tem título, legenda, descrição e alternativa tabular.
- [x] Estados de carregamento e indisponibilidade possuem texto explícito.
- [x] Contraste e foco seguem a identidade brutalista amarela/preta sem remover indicador de foco.
- [x] Testes frontend: 12 testes Vitest aprovados; lint e build TypeScript/Vite aprovados.
- [x] Navegação no explorador desktop verificada sem erros ou avisos no console; alternância SIH/SIM confirmou os rótulos corretos do mapa.
- [x] Nos mapas municipais validados, os 92 municípios publicáveis recebem foco por teclado e `aria-label` com território, taxa e período; células suprimidas não entram na ordem de foco.
- [x] A intensidade do mapa tem legenda textual (“menor”/“maior taxa”) e Volta Redonda permanece diferenciada; a cor não é o único canal de identificação.

## Decisão registrada

- A decisão `approved` está registrada em `reports/reviews/release_signoff.json`.
- Testes adicionais com leitor de tela, zoom 200% e dispositivos móveis permanecem
  recomendados para manutenção contínua e não devem ser interpretados como
  executados por uma auditoria externa nesta release.
