# Handoff de aprovação — Portal Observatório Saúde & Ambiente

Atualização: 2026-08-03  
Release: `beta-cardiorespiratorio-integrado`  
Status: `public_release_ready`

## Estado técnico

- 45 indicadores, 2.700 observações públicas e 93 observações suprimidas.
- 30 indicadores SIM elegíveis para perfis de idade/sexo em 2022.
- 92 municípios no mapa SIM 2022 e 92 no mapa SIH 2022.
- Totais municipais SIH reconciliados com a série anual para 15 desfechos.
- Comparador Brasil SIH presente em 15/15 indicadores.
- Células menores que cinco não chegam ao frontend, CSV ou JSON público.
- Auditoria automática encontrou zero vazamentos de valor, contagem ou intervalo
  em linhas suprimidas do CSV público.
- O ano 2023 permanece como lacuna de denominador; não há interpolação.

## Decisões registradas

1. **Epidemiologia:** aprovada pelo responsável do projeto com base nas
   evidências técnicas da release.
2. **Acessibilidade:** aprovada pelo responsável do projeto com base no audit,
   testes frontend, foco, teclado, mapa, tabelas e downloads disponíveis.

O registro completo, incluindo limitações e escopo, está em
`reports/reviews/release_signoff.json`. A aprovação não afirma auditoria externa
independente; testes adicionais com tecnologia assistiva continuam recomendados.

## Avisos conhecidos

- 2023 não possui denominador municipal compatível nesta release; continuar
  exibindo-o como lacuna até eventual fonte oficial validada.
- 60 observações são provisórias e devem permanecer rotuladas como tais.
- FTP legado SIH, INMET, RHC e dados ocupacionais são fontes futuras fora do
  escopo atual, não entradas para completar a beta por inferência.

## Evidências para a revisão

- `reports/quality/portal_release_preflight.json`
- `reports/quality/portal_accessibility_audit.json`
- `reports/quality/sih_municipal_map_2022_manifest.json`
- `reports/quality/sim_municipal_map_2022_manifest.json`
- `reports/quality/population_denominator_manifest.json`
- `site/public/data/release.json`
- `site/public/data/launch-readiness.json`

## Critério de manutenção

Qualquer alteração de dados ou interface deve regenerar `portal-data`,
`portal-preflight`, testes Python, lint, testes frontend e build. A release atual
retorna `publicationAllowed=true`, com os avisos conhecidos preservados.
