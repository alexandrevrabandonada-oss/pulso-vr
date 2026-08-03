# Observatório Estadual de Saúde do Rio de Janeiro

Estudo reproduzível e observatório estadual sobre internações respiratórias e
cardiovasculares, pandemia, poluição, mortalidade por câncer, assistência
oncológica e exposição ocupacional no Rio de Janeiro. Os 92 municípios ocupam
a mesma posição na experiência pública quando houver dados validados. Volta
Redonda permanece apenas como recorte histórico da pesquisa.

## Status da primeira execução

O workspace original estava vazio, sem bases, documentos ou commits. A
estrutura das Fases 0–1 foi criada, com protocolo preliminar, matriz de
perguntas, catálogo de fontes, configurações, validações automatizadas e
downloaders idempotentes. A Fase 2 já validou a descoberta dinâmica no portal
oficial, adquiriu a série SIM 2010–2024 e arquivos SIVEP versionados de 2019–2026 e confirmou o
código DATASUS de residência de Volta Redonda. Não há resultado etiológico
confirmado: há resultados preliminares descritivos de SIH, SIM e
SIVEP, mas nenhuma hipótese causal é considerada confirmada.

## Comparação e períodos

A comparação primária é o município selecionado versus o restante do Estado do
Rio, sempre excluindo dinamicamente a cidade selecionada do numerador e do
denominador agregados. Não se usa média simples das taxas municipais. Comparações
secundárias incluem o Médio Paraíba sem Volta Redonda, municípios comparáveis
definidos a priori e o Brasil quando numerador e denominador forem equivalentes.
O código IBGE de Volta Redonda usado no SIDRA é `3306305`.

Os períodos completos estão em `config/periods.yml`. Março de 2020 é a ruptura
da análise respiratória; 2020–2022 é período de interrupção assistencial para
câncer; 2025–2026 ou 2025 em diante são provisórios conforme a fonte.
As doenças cardiovasculares têm uma série própria, com 2020–2021 marcado como
contexto pandêmico, sem ser tratado como ruptura causal.
Também há uma série integrada cardiorrespiratória (I00–I99 + J00–J99),
mantendo os componentes respiratório e cardiovascular disponíveis separadamente.

## Instalação e execução

```text
python -m venv .venv
python -m pip install -e .[dev]
python scripts/run_cli.py validate
python scripts/run_cli.py validate-raw
python scripts/run_cli.py validate-layout
python scripts/run_cli.py validate-territories
python scripts/run_cli.py all
python -m pytest -q
```

Com GNU Make:

```text
make validate
make test
make all
```

As aquisições públicas são feitas por comandos idempotentes. Exemplos:

```text
python scripts/run_cli.py acquire --source ibge_9514_vr_2022
python scripts/run_cli.py acquire --source sim_2024_csv
python scripts/run_cli.py acquire --source sivep_2019_parquet
python scripts/run_cli.py sih-query --year 2024 --month 1
python scripts/run_cli.py sih-series --start-year 2024 --start-month 1 --end-year 2024 --end-month 12
python scripts/run_cli.py sih-morbidity --start-year 2008 --start-month 1 --end-year 2017 --end-month 12
python scripts/run_cli.py sih-morbidity --start-year 2018 --start-month 1 --end-year 2026 --end-month 5
python scripts/run_cli.py respiratory-report
python scripts/run_cli.py population-acquire --start-year 2008 --end-year 2025
python scripts/run_cli.py population-harmonize --start-year 2008 --end-year 2025
python scripts/run_cli.py population-age-sex-acquire
python scripts/run_cli.py population-age-sex-harmonize
python scripts/run_cli.py respiratory-rates
python scripts/run_cli.py respiratory-its
python scripts/run_cli.py outcome-counts
python scripts/run_cli.py sivep-summary
python scripts/run_cli.py sivep-monthly
python scripts/run_cli.py sim-mortality-rates
python scripts/run_cli.py sim-age-sex-profile
python scripts/run_cli.py sim-age-sex-rates
python scripts/run_cli.py sim-municipal-map
python scripts/run_cli.py portal-data --release-id beta-local --acquire-geography
python scripts/run_cli.py portal-preflight
# para CI de publicação pública: falha enquanto houver bloqueios
python scripts/run_cli.py portal-preflight --strict
python scripts/run_cli.py harmonize --source all
```

## Portal estático

O portal público está em `site/` e consome exclusivamente os agregados seguros
gerados por `portal-data`. O comando publica `release.json`, catálogo, séries,
perfis, mapa contextual, downloads e hashes em `site/public/data/`; contagens
menores que cinco chegam ao site apenas como valores nulos suprimidos.

```text
cd site
npm install
npm run dev
npm test
npm run build
```

A versão atual está aprovada para publicação estática, com avisos explícitos.
Mortalidade por câncer vem do SIM e não é incidência; o comparador Brasil está
disponível para as séries SIM nacionais.
O comparador Brasil do SIH foi adquirido pela tabela oficial NRBR, agregado por
residência e reconciliado no pipeline. A camada municipal validada disponível é
uma fotografia SIM 2022 por residência (92 municípios, taxa bruta e IC de
Poisson, células menores que cinco suprimidas). A consulta municipal SIH foi
reconciliada com a série anual para 15 desfechos e o snapshot municipal 2022
agora está publicado no mapa. O comando `sim-municipal-map` gera o artefato SIM
auditável; `sih-municipal-map` registra a consulta, os hashes e a reconciliação.
O pré-voo de lançamento grava o diagnóstico em
`reports/quality/portal_release_preflight.json`,
`reports/technical/portal_lancamento.md` e no download público
`site/public/data/launch-readiness.json`. A release atual está aprovada para
publicação estática, com três avisos explícitos; os mapas municipais estão
disponíveis em snapshot 2022. O módulo de perfis cobre os 30 indicadores SIM com dados de
2022; SIH não é apresentado como perfil nesta versão. O ano 2010 usa a
população residente do Censo 2010; 2023 permanece como lacuna de denominador,
sem interpolação.
O inventário resumido de lacunas e critérios de fechamento está em
`reports/technical/lacunas_dados_portal.md`.
As revisões epidemiológica e de acessibilidade, aprovadas pelo responsável do
projeto com base nas evidências técnicas, estão em `reports/reviews/`. O
registro da decisão está em `reports/reviews/release_signoff.json`.

Cada arquivo baixado permanece em `data/raw/`, recebe um arquivo `.sha256` e
é registrado em `metadata/extraction_log.csv`. A aquisição nunca substitui um
arquivo bruto sem validação explícita.

O catálogo atual dos recursos oficiais descobertos está em
`metadata/discovered_resources_sim.json` e
`metadata/discovered_resources_sivep.json`; os layouts observados estão em
`metadata/layout_manifest.json`. A validação territorial está em
`reports/quality/territory_code_validation.md`.
A série mensal SIH harmonizada, sem alterar os arquivos brutos, fica em um
arquivo nomeado por janela em `data/interim/`; a janela 2020–2024 está em
`data/interim/sih_nrrj_monthly_2020_2024.csv` e seu relatório em
`reports/quality/sih_series_2020_2024.json`.
Também estão disponíveis as janelas históricas 2008–2017, 2018–2019 e
2025–2026-05. Os meses de 2026 ainda não listados pelo TabNet não são tratados
como zero.

A harmonização inicial SIM/SIVEP por nome de campo é gravada somente em
`data/interim/`; o manifesto correspondente fica em
`reports/quality/harmonization_manifest.json`.
Os denominadores populacionais agregados são harmonizados a partir das tabelas
SIDRA 6579 e 9514 em `data/processed/`, com manifesto em
`reports/quality/population_denominator_manifest.json`. Anos sem observação
oficial permanecem ausentes e não são interpolados.
As primeiras taxas brutas anuais, com IC exato de Poisson, são gravadas em
`data/processed/respiratory_rates_annual.parquet`. Apenas anos com 12 meses
SIH e denominador disponível entram no cálculo; isso ainda não é padronização
por idade nem análise causal.
O mesmo artefato inclui as categorias cardiovasculares do capítulo I00–I99:
doenças circulatórias, hipertensão, doença isquêmica, infarto agudo do
miocárdio, embolia pulmonar, arritmias, insuficiência cardíaca e doenças
cerebrovasculares. No SIH, os agregados são somas das subcategorias exibidas
pela Lista de Morbidade; no SIM, a classificação usa a causa básica e CID-10.
O indicador integrado cardiorrespiratório soma apenas eventos classificados em
I00–I99 ou J00–J99 dentro da mesma fonte e período.
Os desfechos classificados do SIM e SIVEP ficam em
`data/processed/outcome_counts_sim_sivep.parquet`. SIM representa óbitos; SIVEP
representa vigilância de SRAG, não incidência populacional. A apresentação
suprime células menores que cinco.
O resumo pandêmico do SIVEP fica em
`data/processed/sivep_surveillance_summary.parquet`, com notificações por
residência, taxa de notificação por 100 mil e proporção descritiva de óbitos
entre notificações. A taxa não é incidência e 2019–2026 não deve ser comparado
automaticamente sem considerar cobertura, definição de caso e revisão da base;
2025 permanece provisório e 2026 é parcial na versão de 27/07/2026. O relatório está em
`reports/technical/pandemia_sivep.md`.
Também há uma série mensal SIVEP por mês de início dos sintomas em
`data/processed/sivep_monthly_surveillance.parquet`; ela mantém Covid-19 e
influenza como séries independentes e não é incidência. O relatório está em
`reports/technical/sivep_mensal.md`. A janela termina no último mês observado nos
arquivos adquiridos; para a versão atual, 2026 é parcial e provisório.
As taxas brutas de mortalidade do SIM para os anos públicos observados ficam em
`data/processed/sim_mortality_rates_sample.parquet`, com IC exato de Poisson,
razão VR/restante do RJ e marcação de 2020 como interrupção assistencial ou
pandemia conforme o desfecho. Os arquivos SIM de 2010–2024 foram adquiridos,
mas 2023 permanece fora das taxas por falta de denominador populacional
compatível;
o relatório está em `reports/technical/mortalidade_sim.md`.
O perfil descritivo por grupos etários amplos e sexo está em
`data/processed/sim_mortality_age_sex_profile.parquet`; ele mostra
contagens e proporções dentro do desfecho, sem substituir as taxas específicas
de 2022, que são produzidas em separado.
O relatório está em `reports/technical/perfil_etario_sexual_sim.md`.
Os denominadores por idade e sexo do Censo 2022 são harmonizados da tabela
SIDRA 9514 em `data/processed/population_age_sex_denominators_2022.parquet`.
Eles permitem taxas específicas apenas para 2022; não são interpolados para os
demais anos. O relatório está em
`reports/technical/denominadores_idade_sexo_2022.md`.
As taxas específicas de mortalidade por idade e sexo do SIM 2022, com IC exato
de Poisson e comparação entre Volta Redonda e o restante do RJ, ficam em
`data/processed/sim_mortality_age_sex_rates_2022.parquet`. São taxas brutas
específicas, não padronizadas; o relatório está em
`reports/technical/taxas_sim_idade_sexo_2022.md`.
Também está disponível a primeira série respiratória agregada do SIH em
`data/interim/sih_morbidity_2008_2017.csv` e
`data/interim/sih_morbidity_2018_2026.csv`, com o relatório técnico em
`reports/technical/fase3_respiratorio.md`. Esses arquivos ainda não liberam
taxas específicas do SIH, porque a extração agregada não contém idade/sexo.
A série temporal interrompida respiratória, com ruptura pré-especificada em
março de 2020, está em `data/processed/sih_respiratory_interrupted_series.parquet`
e seus coeficientes estão em
`data/processed/sih_respiratory_interrupted_models.parquet`; o relatório está em
`reports/technical/serie_interrompida_respiratoria.md`. A reconciliação
independente com totais externos ainda permanece pendente.

## Princípios analíticos

- SIH mede internações/AIH de residentes e não pessoas únicas.
- SIM mede óbitos de residentes; bases preliminares não são misturadas às
  definitivas.
- SIVEP-Gripe é analisado como vigilância de SRAG, com mudanças de cobertura e
  formulário documentadas antes de comparar anos.
- Taxas brutas, específicas e padronizadas são mantidas separadas; a
  padronização direta usa o mesmo padrão etário em todos os territórios.
- Associação temporal com poluentes não será descrita como causalidade.
- RHC, Painel Oncologia e SISCAN descrevem assistência/registro e não são
  usados isoladamente para inferir incidência populacional.

## Estrutura

```text
config/                 regras de desfechos, períodos e fontes
data/raw/               arquivos originais imutáveis
data/interim/           dados temporários harmonizados
data/processed/         bases analíticas Parquet
metadata/               catálogo e logs de proveniência
src/vr_saude/           código de produção
tests/                  testes automatizados
reports/                protocolo, qualidade e relatórios
requests/               LAI, ética e parcerias
site/                   portal React/Vite e artefatos públicos estáticos
```

## Limitações atuais

O endpoint FTP legado do SIH não respondeu durante a validação inicial. A rota
TabNet por residência foi automatizada para 2008–2025 e 2026 até maio, mas a
cobertura só será liberada depois de reconciliar os totais com a fonte oficial.
Ainda faltam, entre outros, dados
históricos de qualidade do ar em resolução diária, registros de câncer,
cobertura de planos privados e dados ocupacionais legalmente acessíveis.
