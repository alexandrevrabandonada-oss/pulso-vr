# Fase 2 — aquisição oficial e validação inicial

## Escopo concluído nesta entrega

- Descoberta dinâmica de recursos nas páginas oficiais do SIM e do SIVEP-SRAG.
- Seleção determinística por ano e formato, priorizando Parquet no SIVEP e CSV
  no SIM quando o recurso Parquet não existe.
- Download idempotente, hash SHA-256 e registro no log de extração.
- Inspeção de contêiner, cabeçalho e campos mínimos por fonte.
- Validação do campo de residência e do código DATASUS de Volta Redonda.

## Amostras disponíveis

| Fonte | Período | Formato | Linhas | Código de residência VR |
|---|---:|---|---:|---:|
| SIM | 2010 | ZIP/CSV | 1.136.947 | 1.962 |
| SIM | 2020 | ZIP/CSV | 1.556.824 | 2.704 |
| SIM | 2024 | ZIP/CSV | 1.532.015 | 2.493 |
| SIVEP-SRAG | 2019 | Parquet | 48.941 | 116 |
| SIVEP-SRAG | 2020 | Parquet | 1.206.920 | 1.525 |

Os totais acima são apenas contagens da amostra bruta por residência e não
constituem taxas, incidência, mortalidade ou comparação causal.

## Achado territorial

O campo `CODMUNRES` do SIM e o campo `CO_MUN_RES` do SIVEP apresentam o código
DATASUS de seis dígitos `330630` para Volta Redonda. O código IBGE de sete
dígitos `3306305` continua sendo a referência para SIDRA e para validação
cadastral. A regra de análise permanece residência, sem substituição por
município de ocorrência ou notificação.

## Limites antes da análise

- A diferença de layout entre os anos do SIM exige dicionários por versão.
- Os arquivos SIVEP estão sujeitos a revisão e devem ser tratados como versões
  datadas, sem misturar banco vivo e ano congelado sem decisão explícita.
- Ainda falta reconciliar as contagens com tabulações oficiais e fechar o
  denominador populacional anual/etário.
- O SIH/SUS ainda não possui amostra adquirida nesta entrega.

## Artefatos de auditoria

- `metadata/extraction_log.csv`
- `metadata/discovered_resources_sim.json`
- `metadata/discovered_resources_sivep.json`
- `metadata/layout_manifest.json`
- `reports/quality/territory_code_validation.md`
