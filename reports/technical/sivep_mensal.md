# Série mensal do SIVEP por início dos sintomas

Execução: 2026-08-03T01:53:50+00:00

As notificações são agregadas pelo mês de início dos sintomas (`DT_SIN_PRI`) e pelo município de residência. `srag` inclui todas as notificações elegíveis; Covid-19 e influenza permanecem como séries independentes. A taxa é de notificação, não incidência populacional.

- Janela mensal: **2019-01 a 2026-07**.
- Linhas do Parquet: **819**.
- Anos sem denominador: **[2023, 2026]**.
- 2025 é provisório; 2026 é parcial até **2026-07** na versão adquirida. Eventos fora da janela e datas de início ausentes são registrados no manifesto.
- Células menores que cinco são suprimidas nesta tabela.

## Totais anuais de controle

| ano | território | desfecho | notificações | notificações/100 mil | óbitos entre notificações |
|---:|---|---|---:|---:|---:|
| 2019 | rest_of_rj_excluding_vr | covid19 | <5 | 0.00 | <5 |
| 2019 | volta_redonda | covid19 | <5 | 0.00 | <5 |
| 2019 | rest_of_rj_excluding_vr | influenza | 311 | 1.83 | 71 |
| 2019 | volta_redonda | influenza | 13 | 4.76 | <5 |
| 2019 | rest_of_rj_excluding_vr | srag | 2316 | 13.63 | 309 |
| 2019 | volta_redonda | srag | 116 | 42.49 | 24 |
| 2020 | rest_of_rj_excluding_vr | covid19 | 83048 | 485.88 | 33715 |
| 2020 | volta_redonda | covid19 | 962 | 351.11 | 430 |
| 2020 | rest_of_rj_excluding_vr | influenza | 131 | 0.77 | 26 |
| 2020 | volta_redonda | influenza | <5 | 0.73 | <5 |
| 2020 | rest_of_rj_excluding_vr | srag | 121100 | 708.51 | 40658 |
| 2020 | volta_redonda | srag | 1500 | 547.47 | 581 |
| 2021 | rest_of_rj_excluding_vr | covid19 | 99550 | 579.17 | 36462 |
| 2021 | volta_redonda | covid19 | 2188 | 795.85 | 868 |
| 2021 | rest_of_rj_excluding_vr | influenza | 3071 | 17.87 | 283 |
| 2021 | volta_redonda | influenza | 40 | 14.55 | <5 |
| 2021 | rest_of_rj_excluding_vr | srag | 142840 | 831.02 | 42378 |
| 2021 | volta_redonda | srag | 2990 | 1087.57 | 1035 |
| 2022 | rest_of_rj_excluding_vr | covid19 | 18112 | 114.68 | 6326 |
| 2022 | volta_redonda | covid19 | 659 | 251.95 | 185 |
| 2022 | rest_of_rj_excluding_vr | influenza | 442 | 2.80 | 38 |
| 2022 | volta_redonda | influenza | 11 | 4.21 | <5 |
| 2022 | rest_of_rj_excluding_vr | srag | 37707 | 238.75 | 9966 |
| 2022 | volta_redonda | srag | 1285 | 491.28 | 290 |
| 2023 | rest_of_rj_excluding_vr | covid19 | 3883 | — | 1123 |
| 2023 | volta_redonda | covid19 | 242 | — | 45 |
| 2023 | rest_of_rj_excluding_vr | influenza | 680 | — | 106 |
| 2023 | volta_redonda | influenza | 18 | — | <5 |
| 2023 | rest_of_rj_excluding_vr | srag | 18931 | — | 4062 |
| 2023 | volta_redonda | srag | 733 | — | 119 |
| 2024 | rest_of_rj_excluding_vr | covid19 | 2200 | 12.99 | 483 |
| 2024 | volta_redonda | covid19 | 124 | 44.30 | 27 |
| 2024 | rest_of_rj_excluding_vr | influenza | 1748 | 10.32 | 198 |
| 2024 | volta_redonda | influenza | 47 | 16.79 | <5 |
| 2024 | rest_of_rj_excluding_vr | srag | 17650 | 104.19 | 2339 |
| 2024 | volta_redonda | srag | 597 | 213.29 | 140 |
| 2025 | rest_of_rj_excluding_vr | covid19 | 1008 | 5.95 | 195 |
| 2025 | volta_redonda | covid19 | 60 | 21.43 | 11 |
| 2025 | rest_of_rj_excluding_vr | influenza | 2568 | 15.16 | 338 |
| 2025 | volta_redonda | influenza | 187 | 66.79 | 18 |
| 2025 | rest_of_rj_excluding_vr | srag | 22308 | 131.66 | 2375 |
| 2025 | volta_redonda | srag | 814 | 290.74 | 126 |
| 2026 | rest_of_rj_excluding_vr | covid19 | 427 | — | 87 |
| 2026 | volta_redonda | covid19 | 32 | — | 8 |
| 2026 | rest_of_rj_excluding_vr | influenza | 1406 | — | 74 |
| 2026 | volta_redonda | influenza | 68 | — | <5 |
| 2026 | rest_of_rj_excluding_vr | srag | 11726 | — | 844 |
| 2026 | volta_redonda | srag | 343 | — | 33 |

A diferença entre arquivos anuais vivos, mudanças de cobertura, definição de caso e revisões impede interpretar a série como incidência sem auditoria específica. A análise temporal interrompida mensal do SIVEP permanece uma etapa posterior e não é estimada neste produto.

## Proveniência

- `data\interim\sivep_2019_harmonized.parquet` — SHA-256 `462776c0188faa490418629a21380863ea479cac0605f0a77efdb7ae3ffc2281`
- `data\interim\sivep_2020_harmonized.parquet` — SHA-256 `bb0fb1a7525633bc7b4e70db1992533408792d3d872f2a0933fb6582b267c607`
- `data\interim\sivep_2021_harmonized.parquet` — SHA-256 `cd24265621e9359ce228c3379b5f2df92e79076e1d99d034cdaf0337530ea36e`
- `data\interim\sivep_2022_harmonized.parquet` — SHA-256 `a9d3226cbf8f918b538d9a13b3026fbadb6ddac10c2015492a37a840a755fd7f`
- `data\interim\sivep_2023_harmonized.parquet` — SHA-256 `eca3cf4b869b24d1fb84d6c166fabd650394ccbafa4fd9760f76d964924cc5e1`
- `data\interim\sivep_2024_harmonized.parquet` — SHA-256 `76ccd46080ab1db62e48ad318f361ae60d4a45ae8bdcf7fc0a489d9a2993fa2d`
- `data\interim\sivep_2025_harmonized.parquet` — SHA-256 `22227f3ed2fe885f493412270affce15fadf5b635a9e920483daa628bb02001a`
- `data\interim\sivep_2026_harmonized.parquet` — SHA-256 `afc08323ffb5ae63cc272cf35d0ab69c43537bd8e8c0824dc46e15bbf50d2c71`
