# Revisão epidemiológica — minuta de aprovação

Status: **approved_by_project_owner_technical_evidence**  
Data: 2026-08-03

Esta minuta registra as verificações técnicas e a aprovação do responsável pelo
projeto. Ela não representa revisão epidemiológica independente externa.

## Verificações concluídas

- [x] Município de residência é a unidade territorial de risco em SIM e SIH.
- [x] Comparador primário é `rest_of_rj_excluding_vr`; Volta Redonda não entra no denominador do comparador.
- [x] Comparador Brasil SIH está presente em 15/15 indicadores e usa a tabela NRBR por residência.
- [x] Mapas municipais SIM e SIH usam somente municípios do RJ com denominador residente de 2022.
- [x] Totais do mapa SIH 2022 reconciliam com a série agregada anual para os 15 desfechos.
- [x] Células com contagem menor que cinco são suprimidas antes do frontend e downloads.
- [x] 2010 usa o denominador do Censo 2010; 2023 permanece como lacuna sem
  interpolação por ausência de denominador municipal compatível.
- [x] 2020–2022 e 2025+ estão rotulados conforme as rupturas e o caráter provisório definidos no protocolo.
- [x] SIM é descrito como mortalidade; câncer não é apresentado como incidência.
- [x] SIH é descrito como eventos/AIHs; não como pessoas únicas ou casos novos.
- [x] Não há texto que atribua causalidade ambiental ou ocupacional à CSN.

## Evidências

- `reports/quality/portal_release_preflight.json`
- `reports/quality/sih_municipal_map_2022_manifest.json`
- `reports/quality/sim_municipal_map_2022_manifest.json`
- `site/public/data/catalog.json` e séries JSON correspondentes
- `tests/` e `reports/technical/portal_lancamento.md`

## Decisão registrada

- A decisão `approved` está registrada em `reports/reviews/release_signoff.json`.
- A aprovação é do responsável pelo projeto, com base nas evidências listadas;
  uma revisão independente continua recomendável como manutenção.
