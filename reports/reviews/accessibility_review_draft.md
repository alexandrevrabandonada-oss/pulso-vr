# Revisão de acessibilidade — release estadual de perfis

Status: **pending_manual_revalidation**  
Data da evidência automatizada: 2026-08-03

Esta minuta reúne evidências técnicas da release estadual. Ela não representa
auditoria externa nem aprovação manual. O aceite histórico da release
`beta-cardiorespiratorio-integrado` não se aplica automaticamente a
`statewide-profiles-preview`.

## Evidências automatizadas concluídas

- [x] Rotas públicas possuem conteúdo principal e um único `h1`.
- [x] Visão municipal não seleciona Volta Redonda silenciosamente.
- [x] Perfis exigem seleção explícita de município.
- [x] Tabelas oferecem alternativa textual aos gráficos.
- [x] Células suprimidas não expõem contagem, taxa ou intervalo no payload público.
- [x] Comparador estadual é recalculado como `RJ sem o município selecionado`.
- [x] Navegação municipal e perfis foram verificadas em 360 px e 768 px sem rolagem horizontal.
- [x] Testes Python: 51 aprovados em worktree limpo.
- [x] Testes frontend: 28 aprovados; lint e build TypeScript/Vite aprovados.
- [x] Bundle JavaScript inicial: 76,19 kB gzip, abaixo do orçamento de 200 kB gzip.

## Revisão manual obrigatória antes da publicação

- [ ] Executar a jornada completa somente por teclado e verificar ordem de foco e restauração ao fechar filtros.
- [ ] Validar home, município, explorador e perfis com leitor de tela.
- [ ] Verificar zoom de 200% sem perda de conteúdo ou controles.
- [ ] Revisar contraste de texto, foco, estados desabilitados e visualizações.
- [ ] Confirmar alvos interativos de pelo menos 44 × 44 px em dispositivo móvel.
- [ ] Confirmar que mapa e gráficos não dependem exclusivamente de cor.
- [ ] Registrar navegador, leitor de tela, sistema operacional, responsável, data e achados.

## Decisão

A revisão permanece **pendente**. Somente o responsável designado pode alterar
o gate `accessibilityReview` para `approved` após concluir e registrar os itens
manuais acima. Até lá, a release deve permanecer `blocked_for_public_release`.
