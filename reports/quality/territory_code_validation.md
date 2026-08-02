# Validação dos códigos territoriais

Esta checagem confirma que os filtros de residência encontram Volta Redonda nos arquivos brutos.

- Código DATASUS esperado no campo de residência: `330630`.
- Código IBGE de referência cadastral: `3306305`.
- O código observado nos campos SIM `CODMUNRES` e SIVEP `CO_MUN_RES` é o código DATASUS de seis dígitos.

| Arquivo | Fonte/campo | Linhas | Linhas VR | Tamanhos observados | Status |
|---|---|---:|---:|---|---|
| `sim_2010_Mortalidade_Geral_2010_csv.zip` | SIM / `CODMUNRES` | 1136947 | 1962 | `{"6": 1136947}` | OK |
| `sim_2020_Mortalidade_Geral_2020_csv.zip` | SIM / `CODMUNRES` | 1556824 | 2704 | `{"6": 1556824}` | OK |
| `sim_mortalidade_geral_2024_csv.zip` | SIM / `CODMUNRES` | 1532015 | 2493 | `{"6": 1532015}` | OK |
| `sivep_2020_INFLUD20-23-03-2026.parquet` | SIVEP-SRAG / `CO_MUN_RES` | 1206920 | 1525 | `{"0": 113, "6": 1206807}` | OK |
| `sivep_srag_2019_2026-03-23.parquet` | SIVEP-SRAG / `CO_MUN_RES` | 48941 | 116 | `{"0": 37, "6": 48904}` | OK |
