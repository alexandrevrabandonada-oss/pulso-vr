# Validação de amostras brutas

Esta validação testa sidecar SHA-256 e integridade estrutural básica; não substitui a reconciliação epidemiológica com totais oficiais.

| arquivo | bytes | hash | formato | status | detalhes |
|---|---:|---|---|---|---|
| ibge_sidra_9514_vr_2022.json | 945 | OK | OK | OK | {"json_type": "list"} |
| sim_mortalidade_geral_2024_csv.zip | 98076266 | OK | OK | OK | {"first_members": ["DO24OPEN.csv"], "members": 1} |
| sivep_srag_2019_2026-03-23.parquet | 3447406 | OK | OK | OK | {"columns": 194, "row_groups": 1, "rows": 48941} |
| sivep_srag_dicionario_2019_2025.pdf | 1052922 | OK | OK | OK | {"header": "%PDF-"} |
