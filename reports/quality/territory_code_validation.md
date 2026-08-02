# Validação dos códigos territoriais

Esta checagem confirma que os filtros de residência encontram Volta Redonda nos arquivos brutos.

- Código DATASUS esperado no campo de residência: `330630`.
- Código IBGE de referência cadastral: `3306305`.
- O código observado nos campos SIM `CODMUNRES` e SIVEP `CO_MUN_RES` é o código DATASUS de seis dígitos.

| Arquivo | Fonte/campo | Linhas | Linhas VR | Tamanhos observados | Status |
|---|---|---:|---:|---|---|
| `sim_2010_Mortalidade_Geral_2010_csv.zip` | SIM / `CODMUNRES` | 1136947 | 1962 | `{"6": 1136947}` | OK |
| `sim_2011_Mortalidade_Geral_2011_csv.zip` | SIM / `CODMUNRES` | 1170498 | 1997 | `{"6": 1170498}` | OK |
| `sim_2012_Mortalidade_Geral_2012_csv.zip` | SIM / `CODMUNRES` | 1181166 | 1916 | `{"6": 1181166}` | OK |
| `sim_2013_Mortalidade_Geral_2013_csv.zip` | SIM / `CODMUNRES` | 1210474 | 2025 | `{"6": 1210474}` | OK |
| `sim_2014_Mortalidade_Geral_2014_csv.zip` | SIM / `CODMUNRES` | 1227039 | 2013 | `{"6": 1227039}` | OK |
| `sim_2015_Mortalidade_Geral_2015_csv.zip` | SIM / `CODMUNRES` | 1264175 | 2050 | `{"6": 1264175}` | OK |
| `sim_2016_Mortalidade_Geral_2016_csv.zip` | SIM / `CODMUNRES` | 1309774 | 2120 | `{"6": 1309774}` | OK |
| `sim_2017_Mortalidade_Geral_2017_csv.zip` | SIM / `CODMUNRES` | 1312663 | 2081 | `{"6": 1312663}` | OK |
| `sim_2018_Mortalidade_Geral_2018_csv.zip` | SIM / `CODMUNRES` | 1316719 | 2279 | `{"6": 1316719}` | OK |
| `sim_2019_Mortalidade_Geral_2019_csv.zip` | SIM / `CODMUNRES` | 1349801 | 2369 | `{"6": 1349801}` | OK |
| `sim_2020_Mortalidade_Geral_2020_csv.zip` | SIM / `CODMUNRES` | 1556824 | 2704 | `{"6": 1556824}` | OK |
| `sim_2021_Mortalidade_Geral_2021_csv.zip` | SIM / `CODMUNRES` | 1832649 | 3202 | `{"6": 1832649}` | OK |
| `sim_mortalidade_geral_2024_csv.zip` | SIM / `CODMUNRES` | 1532015 | 2493 | `{"6": 1532015}` | OK |
| `sivep_2020_INFLUD20-23-03-2026.parquet` | SIVEP-SRAG / `CO_MUN_RES` | 1206920 | 1525 | `{"0": 113, "6": 1206807}` | OK |
| `sivep_srag_2019_2026-03-23.parquet` | SIVEP-SRAG / `CO_MUN_RES` | 48941 | 116 | `{"0": 37, "6": 48904}` | OK |
