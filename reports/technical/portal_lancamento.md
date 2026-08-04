# Pré-voo de lançamento do Portal Observatório Saúde & Ambiente

Verificação: `2026-08-04T01:07:14+00:00`
Release: `statewide-2026-08-03`
Status: **public_release_ready**

## Resumo

- Bloqueios públicos: **0**
- Avisos: **3**
- Indicadores: **49**
- Observações públicas: **5580**
- Células suprimidas: **1603**
- Indicadores SIM elegíveis para perfis: **32**
- Observações de perfis idade/sexo: **47104**
- Valores municipais no mapa: **2662**
- Células municipais suprimidas no mapa: **1846**
- Comparadores Brasil no SIH: **17/17**
- Vazamentos de supressão no download: **0**

## Achados

### [WARNING] Existem anos sem denominador oficial

2023

Ação: Manter esses anos como lacunas; para 2023, monitorar eventual publicação oficial compatível e regenerar as séries somente após validação, sem interpolar.

### [WARNING] O catálogo de fontes ainda tem itens fora de verified

sih_legacy_ftp=failed_initial_check, inmet=pending_endpoint, rhc=to_request, occupational_data=to_request, sia_ambulatory_alzheimer=unavailable_no_validated_diagnostic_dimension

Ação: Resolver ou marcar claramente como fonte futura fora do escopo da release.

### [WARNING] A série contém observações provisórias

60 observações com dataStatus=provisional.

Ação: Manter o rótulo provisório e indicar a data de atualização da fonte.

## Escopo seguro da release

- Séries agregadas por residência, sem dados pessoais.
- SIH interpretado como eventos/AIHs; SIM interpretado como mortalidade, não incidência.
- O módulo de perfis idade/sexo cobre o SIM em 2022; SIH não é apresentado como perfil neste lançamento.
- Células com contagem menor que cinco não chegam ao frontend.
- Anos sem denominador permanecem como lacunas, sem interpolação.
- Nenhuma associação ecológica autoriza atribuir causalidade à CSN ou a outra fonte.

## Critério de liberação

A publicação pública só é permitida quando `publicationAllowed=true`, os portões de revisão estiverem aprovados e os textos do portal refletirem o escopo efetivamente coberto.
