# Protocolo preliminar — Observatório estadual de saúde cardiorrespiratória,
# respiratória e câncer

**Versão:** 0.1.0  
**Data:** 2026-08-02  
**Status:** protocolo preliminar; sem resultados epidemiológicos liberados

## 1. Pergunta e desenho

O estudo avaliará a distribuição de internações respiratórias e
cardiovasculares e mortalidade por câncer entre os residentes dos 92 municípios
do Estado do Rio de Janeiro. Volta Redonda será o município de referência para
as análises aprofundadas e será comparada com o restante do estado, excluindo
Volta Redonda. Será um programa de
análises observacionais com três componentes:

1. séries populacionais de internações e óbitos por residência para cada
   município, com agregados estaduais e nacionais equivalentes;
2. séries temporais de SRAG, vírus respiratórios, poluição e meteorologia;
3. avaliação de assistência oncológica e, se autorizada, estudo ocupacional.

O desenho permite estimar diferenças e associações. Não permite atribuir
causalidade à CSN ou a um poluente a partir de comparações ecológicas.

## 2. População e comparadores

- População principal: moradores dos 92 municípios do RJ; Volta Redonda,
  município IBGE `3306305`, é o município de referência.
- Comparador primário: moradores dos demais municípios do RJ.
- Comparadores secundários: Médio Paraíba sem Volta Redonda, municípios
  comparáveis selecionados antes da inspeção dos desfechos e evolução interna.
- A unidade territorial de risco é residência. Internações em hospitais de
  outros municípios serão mantidas quando o residente for de Volta Redonda.
- A visão municipal exibirá contagem, taxa bruta, intervalo de confiança,
  população e posição descritiva no conjunto de municípios publicáveis.

## 3. Desfechos

Os códigos respiratórios, cardiovasculares e oncológicos estão em `config/outcomes.yml`. A CID
será normalizada apenas mecanicamente; a equivalência entre layouts de SIH,
SIM e SIVEP será documentada por fonte e ano.

- Respiratório: J00–J99, pneumonias, bronquite/bronquiolite agudas, DPOC,
  asma e pneumoconioses.
- Covid-19 e SRAG: séries independentes.
- Cardiovascular: I00–I99, hipertensão, doença isquêmica do coração, infarto
  agudo do miocárdio, embolia pulmonar, arritmias, insuficiência cardíaca e
  doenças cerebrovasculares.
- Cardiorrespiratório integrado: I00–I99 ou J00–J99, como indicador agregado
  complementar; os componentes não são somados entre fontes.
- Câncer: C00–C97, pulmão, bexiga, leucemias, linfomas, mieloma,
  mielodisplasia, colorretal, estômago, fígado, pâncreas, mama, colo do útero
  e próstata.

## 4. Períodos e rupturas

Os períodos respiratórios, cardiovasculares e oncológicos estão em `config/periods.yml`. Março
de 2020 será modelado como interrupção da série respiratória. Para câncer,
2020–2022 será mantido como período de interrupção assistencial; março de 2022
será o marco da Linha de Atenção Oncológica; 2025 em diante será interpretado
com cautela por causa do Prevenir 50+.
Para cardiovasculares, 2020–2021 será mantido como contexto pandêmico e de
acesso assistencial, sem interpretação causal automática.

## 5. Dados

Serão priorizadas fontes oficiais: SIH/SUS, SIM, IBGE/SIDRA, SIVEP-Gripe,
INEA/SEMEAR ou equivalente oficial de qualidade do ar, INMET, Atlas do INCA,
RHC, Painel Oncologia, SISCAN, CNES, produção ambulatorial/hospitalar,
vacinação e documentos de exposição. O catálogo atual está em
`metadata/source_catalog.csv`.

### SIH/SUS

Baixar, quando disponível, AIH reduzida de residentes no RJ, mensalmente,
2008–2026. O mês é de processamento e geralmente se aproxima da alta, mas não
é idêntico em reapresentações, atrasos e longa permanência. Contagens serão
conciliadas com TabNet antes de qualquer taxa.

### SIM

Baixar óbitos de residentes no RJ, causas básica e múltiplas quando públicas,
2010 em diante para câncer e 2008 em diante para controles. Versões
definitivas, preliminares e provisórias serão identificadas em coluna própria.

### IBGE/SIDRA

Usar população anual para denominadores brutos e específicos; usar população
por idade/sexo com um padrão comum para padronização direta. O Censo 2022,
SIDRA 9514, é a referência de estrutura etária a validar; a SIDRA 6579 é a
fonte de estimativas anuais. Nenhum denominador faltante será substituído por
suposição não registrada.

### SIVEP-Gripe/SRAG

Separar arquivos congelados por ano do banco vivo. Classificar Covid,
influenza, VSR, outros vírus, negativos e ignorados conforme o dicionário da
versão correspondente. Mudanças de ficha, cobertura e atraso de encerramento
serão tratadas como limitações e, quando possível, como rupturas.

## 6. Análises

- Taxas brutas e específicas por 100 mil; IC de Poisson.
- Razão de taxas, diferença absoluta e excesso atribuível descritivo.
- Comparação de cada município com o restante do RJ e, quando equivalente, com
  o Brasil; “média estadual” não será calculada como média simples das taxas
  municipais.
- Padronização direta com o mesmo padrão etário nos dois territórios.
- Regressão segmentada e série temporal interrompida para tendências.
- Séries diárias de poluição com defasagens 0–7 e 0–14 dias, controlando
  tendência, sazonalidade, temperatura, umidade, dia da semana, feriados,
  vírus e pandemia. A distribuição será escolhida após diagnóstico de
  sobredispersão e autocorrelação.
- Câncer: períodos de cinco anos para desfechos raros, mortalidade prematura
  e anos potenciais de vida perdidos. Não correlacionar poluição e câncer do
  mesmo ano como se houvesse latência curta.
- Assistência: estágio, diagnóstico–tratamento, proporção acima de 60 dias,
  cobertura por hospital e ano. Aumento de detecção será separado de aumento
  de incidência.

## 7. Controle de qualidade

Antes de publicar: validar códigos territoriais e CID, residência, completude
temporal, denominador, duplicações, faltantes, totais oficiais, intervalos de
confiança, análise de sensibilidade, supressão de células pequenas e limites
do desenho. Cada resultado terá ligação ao arquivo bruto, código, versão,
data e parâmetros no `outputs/results_manifest.json`.

## 8. Ética e governança

Somente dados públicos anonimizados e agregados serão processados inicialmente.
Dados ocupacionais individuais, registros hospitalares identificáveis e
qualquer chave de linkage dependem de base jurídica, controle de acesso,
acordo institucional e aprovação ética. O plano correspondente está em
`requests/ethics/` e `requests/lai/`.

## 9. Produtos previstos

Catálogo, dicionários, relatório de qualidade, plano estatístico, tabelas CSV
e XLSX, figuras acessíveis, relatório técnico, resumo executivo, versão pública,
mapa e tabela dos 92 municípios, fichas municipais, minutas de LAI, lista de
faltantes, anexo de limitações e manifesto de resultados. A release atual
libera apenas os snapshots municipais validados descritos no inventário de
lacunas; séries municipais históricas continuam como próxima etapa.
