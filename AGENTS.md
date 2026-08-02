# AGENTS.md — vr_saude_ambiental

## Escopo

Este repositório documenta e executa o estudo epidemiológico, estatístico,
ambiental e ocupacional sobre a saúde da população residente em Volta
Redonda (RJ). O código deve produzir tabelas, figuras, relatórios e um
manifesto de resultados a partir de fontes versionadas e rastreáveis.

## Regras obrigatórias

- Município de residência é a unidade de risco populacional; local de
  atendimento ou ocorrência nunca substitui residência.
- Uma internação SIH é um evento/AIH, não uma pessoa única nem um caso novo.
- RHC não é tratado como incidência populacional.
- O comparador primário é todo o RJ menos Volta Redonda. O código IBGE de
  Volta Redonda é `3306305`; o código DATASUS de seis dígitos deve ser
  confirmado a partir do cadastro de municípios antes da análise final.
- A pasta `data/raw` é imutável. Arquivos baixados recebem SHA-256 e não são
  editados, sobrescritos ou normalizados in place.
- Dados definitivos, preliminares e provisórios devem permanecer separados.
- Março de 2020 é a ruptura respiratória da pandemia. Para câncer,
  2020–2022 é período de interrupção assistencial; março de 2022 é o marco da
  Linha de Atenção Oncológica; 2025 em diante é influenciado pela expansão do
  Prevenir 50+ e deve ser tratado como provisório quando aplicável.
- Associações ecológicas não autorizam atribuir causalidade à CSN.
- Células pequenas são suprimidas ou agregadas antes de qualquer publicação.
- Nunca versionar dados restritos, dados pessoais, credenciais, tokens ou
  arquivos de acesso institucional.

## Organização do trabalho

- `config/`: desfechos, períodos, fontes e regras territoriais.
- `data/raw/`: arquivos originais, imutáveis, com sidecar `.sha256`.
- `data/interim/`: conversões temporárias e layouts harmonizados.
- `data/processed/`: bases analíticas em Parquet, particionadas por fonte e ano.
- `metadata/`: catálogo de fontes, logs de extração e dicionários.
- `src/vr_saude/`: código de produção; notebooks são exploratórios.
- `reports/`: protocolo, plano estatístico, qualidade e relatórios públicos.
- `requests/`: minutas de LAI, ética e parcerias.

## Comandos

Após instalar o projeto (`python -m pip install -e .[dev]`):

```text
python scripts/run_cli.py validate
python scripts/run_cli.py all
python -m pytest -q
```

Em ambientes com GNU Make, `make validate`, `make test` e `make all` são os
atalhos equivalentes.

## Fonte e proveniência

Toda nova fonte deve ser adicionada a `metadata/source_catalog.csv` com URL,
título, instituição, data de acesso, versão/atualização, cobertura e
limitações. Toda aquisição deve gerar uma entrada em
`metadata/extraction_log.csv` com status, caminho bruto e SHA-256.

## Qualidade

Antes de aceitar um resultado, validar códigos territoriais e CID, residência,
período, denominador, duplicações, faltantes, reconciliação com totais
oficiais, intervalos de confiança e análises de sensibilidade. Resultados
negativos, falhas e inconsistências são parte do produto final.
