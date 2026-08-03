# Proposta de produto — Observatório de doenças cardiorrespiratórias, respiratórias e câncer

**Versão:** 0.2.0  
**Data:** 2026-08-03  
**Status:** expansão de escopo; dados municipais continuam sujeitos à validação por fonte e período

## 1. Visão

O portal deixa de ser um painel centrado em uma única cidade e passa a ser um
observatório público da saúde respiratória, cardiovascular e oncológica no
Estado do Rio de Janeiro. Cada um dos 92 municípios do estado tem a mesma
posição na navegação e uma visão própria, comparável e rastreável. Volta Redonda
permanece como um dos municípios disponíveis e como recorte histórico da pesquisa.

O observatório deve responder, para cada desfecho e período disponível:

- quantas internações/AIHs de residentes foram registradas;
- quantos óbitos de residentes foram registrados;
- qual foi a taxa bruta por 100 mil habitantes e seu intervalo de confiança;
- como o município se compara ao restante do RJ e ao Brasil, quando a fonte
  nacional for equivalente;
- quais limitações, lacunas, supressões e status de atualização condicionam a leitura.

## 2. Arquitetura de informação

| Camada | Pergunta | Produto de interface |
|---|---|---|
| Estado | Onde estão as maiores e menores taxas publicáveis? | Mapa dos 92 municípios, ranking e tabela pesquisável |
| Município | O que acontece em uma cidade escolhida? | Ficha municipal com contagem, taxa, IC, população e comparadores |
| Desfecho | Qual doença está sendo observada? | Indicadores respiratórios, cardiovasculares, cardiorrespiratórios e câncer |
| Tempo | Como o indicador mudou? | Série anual/mensal, marcos de pandemia e períodos assistenciais |
| Método | O que este número permite concluir? | Fonte, definição CID, residência, denominador, supressão e limitações |

## 3. Escopo epidemiológico

### Internações

O SIH/SUS será apresentado como número de internações/AIHs de residentes.
Uma AIH é um evento administrativo e não representa uma pessoa única nem um
caso novo. O município exibido será sempre o de residência, ainda que a
internação ocorra em outro município.

### Óbitos

O SIM será apresentado como número de óbitos de residentes pela causa básica,
com possibilidade de desdobramento por grupos de idade e sexo quando o
denominador permitir. Mortalidade por câncer não será rotulada como incidência.

### Grupos de doenças

- respiratórias: J00–J99, pneumonias, DPOC, asma e pneumoconioses;
- cardiovasculares: I00–I99, hipertensão, doença isquêmica, infarto,
  insuficiência cardíaca, arritmias, embolia pulmonar e cerebrovasculares;
- cardiorrespiratórias: indicador integrado I00–I99 + J00–J99, sempre com os
  componentes disponíveis separadamente;
- cânceres: C00–C97 e sítios prioritários, incluindo pulmão, bexiga,
  colorretal, estômago, fígado, pâncreas, mama, colo do útero e próstata.

## 4. Comparações e linguagem do produto

O comparador estadual primário é o agregado de todos os municípios do RJ,
excluindo o município selecionado. O comparador Brasil é o agregado nacional da mesma
fonte e definição, quando validado.

O portal não usará “média do estado” para designar uma média simples das taxas
municipais. A linguagem padrão será:

- **taxa do restante do RJ:** numerador e população agregados, sem o município selecionado;
- **taxa do Brasil:** numerador e população nacionais equivalentes;
- **razão da taxa:** taxa municipal dividida pela taxa do comparador;
- **diferença da taxa:** taxa municipal menos a taxa do comparador;
- **ranking:** posição descritiva entre municípios com valor publicável no mesmo
  desfecho e período, nunca uma medida causal ou de desempenho.

Quando houver células pequenas, a contagem, taxa e intervalo serão suprimidos
antes de chegar ao navegador. O ranking indicará “não publicável” e não tratará
o valor suprimido como zero.

## 5. Roadmap de entrega

### Release atual — base municipal validada

- 92 municípios na malha do RJ;
- snapshot municipal SIM 2022 para os desfechos validados;
- snapshot municipal SIH 2022 para os desfechos reconciliados;
- contagem bruta, taxa bruta, intervalo de Poisson e população residente;
- comparação agregada com RJ sem o município selecionado e Brasil quando disponível;
- ficha municipal, busca por cidade, ranking descritivo e link compartilhável
  com o município selecionado.

### Próxima etapa — séries municipais

- série anual municipal para todos os desfechos prioritários;
- séries anuais municipais e seleção de município persistida em link compartilhável;
- ranking por ano e indicador com tratamento explícito de empates e supressões;
- downloads municipais separados por fonte, ano e status definitivo/provisório.

### Etapa analítica

- taxas específicas e padronizadas por idade;
- perfis municipais por sexo e grupos etários;
- camadas assistenciais de câncer separadas de mortalidade;
- integração documentada com qualidade do ar, meteorologia e vigilância de SRAG.

## 6. Guardrails de publicação

Nenhum mapa ou ranking municipal será publicado sem validação dos 92 códigos,
residência, CID, denominador, completude temporal, reconciliação com totais
oficiais e aplicação da supressão de células pequenas. Resultados ecológicos
não atribuem causalidade à CSN, à poluição ou a qualquer exposição individual.
