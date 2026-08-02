# vr_saude_ambiental

Estudo reproduzível sobre internações respiratórias, pandemia, poluição,
mortalidade por câncer, assistência oncológica e exposição ocupacional em
Volta Redonda, Rio de Janeiro.

## Status da primeira execução

O workspace original estava vazio, sem bases, documentos ou commits. A
estrutura das Fases 0–1 foi criada, com protocolo preliminar, matriz de
perguntas, catálogo de fontes, configurações, validações automatizadas e
downloaders idempotentes. A Fase 2 já validou a descoberta dinâmica no portal
oficial, adquiriu amostras SIM 2010/2020/2024 e SIVEP 2019/2020 e confirmou o
código DATASUS de residência de Volta Redonda. Ainda não há resultado
epidemiológico: a rota SIH foi exercitada em um mês, mas nenhuma hipótese é
considerada confirmada.

## Comparação e períodos

A comparação primária é Volta Redonda versus o restante do Estado do Rio,
excluindo Volta Redonda. Comparações secundárias incluem o Médio Paraíba sem
Volta Redonda, municípios comparáveis definidos a priori e a evolução interna
do município. O código IBGE de Volta Redonda usado no SIDRA é `3306305`.

Os períodos completos estão em `config/periods.yml`. Março de 2020 é a ruptura
da análise respiratória; 2020–2022 é período de interrupção assistencial para
câncer; 2025–2026 ou 2025 em diante são provisórios conforme a fonte.

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
```

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
```

## Limitações atuais

O endpoint FTP legado do SIH não respondeu durante a validação inicial. A rota
TabNet por residência foi automatizada e testada para um mês, mas a cobertura
mensal integral do SIH só será liberada depois de iterar os arquivos e
reconciliar os totais com a fonte oficial. Ainda faltam, entre outros, dados
históricos de qualidade do ar em resolução diária, registros de câncer,
cobertura de planos privados e dados ocupacionais legalmente acessíveis.
