# Taxas respiratórias brutas

Execução: 2026-08-02T21:56:36+00:00

A taxa é calculada como internações agregadas do SIH / população residente × 100.000. O intervalo é exato de Poisson para a contagem. A razão compara a taxa de VR com a do restante do RJ, que exclui o código IBGE 3306305.

- Anos elegíveis: **[2008, 2009, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2024, 2025]**.
- Anos SIH parciais excluídos da taxa anual: **[2026]**.
- Anos completos sem denominador excluídos: **[2010, 2023]**.
- Linhas duplicadas removidas ao combinar as janelas SIH: **18**.
- 2025 é marcado como provisório; 2026-01 a 2026-05 não é anualizado.

## Desfecho primário: todas as doenças respiratórias

| ano | território | internações | taxa/100 mil | IC 95%/100 mil |
|---:|---|---:|---:|---:|
| 2008 | rest_of_rj_excluding_vr | 74244 | 475.54 | 472.13–478.97 |
| 2008 | volta_redonda | 1509 | 580.81 | 551.87–610.87 |
| 2009 | rest_of_rj_excluding_vr | 76894 | 488.25 | 484.80–491.71 |
| 2009 | volta_redonda | 1556 | 595.25 | 566.04–625.58 |
| 2011 | rest_of_rj_excluding_vr | 67616 | 426.50 | 423.29–429.73 |
| 2011 | volta_redonda | 1540 | 594.57 | 565.24–625.02 |
| 2012 | rest_of_rj_excluding_vr | 62862 | 393.60 | 390.53–396.69 |
| 2012 | volta_redonda | 1350 | 518.87 | 491.56–547.31 |
| 2013 | rest_of_rj_excluding_vr | 55895 | 347.01 | 344.14–349.90 |
| 2013 | volta_redonda | 1198 | 458.09 | 432.51–484.78 |
| 2014 | rest_of_rj_excluding_vr | 53800 | 332.12 | 329.32–334.94 |
| 2014 | volta_redonda | 1248 | 475.87 | 449.83–503.02 |
| 2015 | rest_of_rj_excluding_vr | 56266 | 345.46 | 342.62–348.33 |
| 2015 | volta_redonda | 1216 | 462.41 | 436.78–489.15 |
| 2016 | rest_of_rj_excluding_vr | 50888 | 310.82 | 308.12–313.53 |
| 2016 | volta_redonda | 1276 | 483.96 | 457.77–511.26 |
| 2017 | rest_of_rj_excluding_vr | 46231 | 280.98 | 278.42–283.55 |
| 2017 | volta_redonda | 1375 | 518.47 | 491.43–546.62 |
| 2018 | rest_of_rj_excluding_vr | 50993 | 301.95 | 299.33–304.58 |
| 2018 | volta_redonda | 1330 | 488.97 | 463.05–515.98 |
| 2019 | rest_of_rj_excluding_vr | 51843 | 305.10 | 302.48–307.74 |
| 2019 | volta_redonda | 1814 | 664.44 | 634.21–695.74 |
| 2020 | rest_of_rj_excluding_vr | 41312 | 241.70 | 239.38–244.04 |
| 2020 | volta_redonda | 967 | 352.94 | 331.04–375.90 |
| 2021 | rest_of_rj_excluding_vr | 45583 | 265.20 | 262.77–267.64 |
| 2021 | volta_redonda | 1214 | 441.57 | 417.08–467.13 |
| 2022 | rest_of_rj_excluding_vr | 68149 | 431.50 | 428.26–434.75 |
| 2022 | volta_redonda | 1773 | 677.85 | 646.66–710.15 |
| 2024 | rest_of_rj_excluding_vr | 68043 | 401.68 | 398.66–404.71 |
| 2024 | volta_redonda | 2329 | 832.09 | 798.63–866.58 |
| 2025 | rest_of_rj_excluding_vr | 70294 | 414.87 | 411.81–417.95 |
| 2025 | volta_redonda | 2233 | 797.58 | 764.84–831.37 |

As taxas por pneumonia, bronquite/bronquiolite aguda, DPOC, asma e pneumoconiose estão no Parquet processado. Células pequenas devem ser suprimidas ou agregadas antes de qualquer publicação; este relatório não publica tabelas anuais desses subgrupos raros.

## Fontes intermediárias

- `data\interim\sih_morbidity_2008_2017.csv` — SHA-256 `fac4ff0a020d6717230b77c3617400d4995496677f15cb8536c6e20877d1aaa8`
- `data\interim\sih_morbidity_2018_2026.csv` — SHA-256 `4d82442080e1c5fa0a994766b7efcbdfee3e01a76d830a30321bcc16a0e0a5e5`
- `data\interim\sih_morbidity_2024_2024.csv` — SHA-256 `77038aa2aa0b531fbe39f27b270d73cf14a6871df2c7eb8a39bd0d15a112b705`

Não há ajuste por idade, sexo, sazonalidade, pandemia ou poluição nesta etapa. Uma taxa bruta não sustenta comparação causal nem substitui a padronização etária.
