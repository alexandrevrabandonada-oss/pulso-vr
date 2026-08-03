# Série temporal interrompida — internações respiratórias do SIH

Execução: 2026-08-03T03:02:02+00:00

O modelo usa contagens mensais de internações/AIH de residentes, com offset da população anual dividida por 12, indicadores de março de 2020 e tendência pós-intervenção, além de indicadores mensais de sazonalidade. Os intervalos usam covariância robusta HAC com 12 defasagens quando disponível.

A razão de tendência é multiplicativa por mês. A razão de nível imediato compara o salto estimado em março de 2020 com o contrafactual da tendência pré-pandemia. Isto é uma análise temporal descritiva/associativa: não estima efeito causal da pandemia, de poluentes ou da CSN.

- Ruptura definida a priori: **2020-03**.
- Anos completos no SIH: **[2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]**.
- Anos elegíveis no modelo: **[2008, 2009, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2024, 2025]**.
- Anos completos sem denominador e excluídos: **[2010, 2023]**.
- Anos parciais e excluídos: **[2026]**.
- 2025 é provisório; 2026-01 a 2026-05 não é anualizado nem modelado.
- SIH conta AIH/internações agregadas, não pessoas únicas nem casos novos.

## Resultados dos modelos

Células com menos de cinco eventos totais não são publicadas. As estimativas abaixo devem ser interpretadas junto com a dispersão, cobertura temporal e mudanças assistenciais.

| território | desfecho | eventos | tendência pré/mês | nível em mar-2020 | tendência pós/mês |
|---|---|---:|---:|---:|---:|
| rest_of_rj_excluding_vr | acute_bronchitis_bronchiolitis | 53794 | 1.002 (1.001–1.004) | 0.679 (0.398–1.157) | 1.016 (1.006–1.025) |
| volta_redonda | acute_bronchitis_bronchiolitis | 1218 | 1.004 (1.000–1.008) | 0.533 (0.272–1.047) | 1.021 (1.009–1.032) |
| rest_of_rj_excluding_vr | asthma | 64558 | 0.984 (0.983–0.986) | 1.412 (0.816–2.442) | 1.008 (0.999–1.017) |
| volta_redonda | asthma | 1564 | 1.008 (1.003–1.012) | 0.867 (0.476–1.581) | 1.006 (0.997–1.016) |
| rest_of_rj_excluding_vr | copd | 69640 | 0.990 (0.988–0.992) | 0.606 (0.389–0.946) | 1.013 (1.008–1.019) |
| volta_redonda | copd | 1491 | 0.996 (0.990–1.001) | 0.978 (0.481–1.988) | 1.014 (1.005–1.023) |
| rest_of_rj_excluding_vr | pneumoconiosis | 670 | 1.012 (1.003–1.021) | 0.939 (0.555–1.588) | 0.990 (0.982–0.998) |
| volta_redonda | pneumoconiosis | 20 | 1.030 (1.013–1.048) | 0.069 (0.013–0.365) | 1.038 (1.015–1.062) |
| rest_of_rj_excluding_vr | pneumonia | 545403 | 0.996 (0.995–0.997) | 1.001 (0.790–1.270) | 1.007 (1.003–1.011) |
| volta_redonda | pneumonia | 12116 | 0.999 (0.997–1.001) | 0.783 (0.601–1.019) | 1.014 (1.010–1.018) |
| rest_of_rj_excluding_vr | resp_all | 940913 | 0.996 (0.995–0.997) | 0.974 (0.764–1.242) | 1.008 (1.005–1.012) |
| volta_redonda | resp_all | 23928 | 1.000 (0.998–1.001) | 0.746 (0.558–0.996) | 1.013 (1.009–1.018) |

## Proveniência

- `data\interim\sih_morbidity_2008_2017.csv` — SHA-256 `b28d4dfc8b7fb7aeca4a90a470e42f203c15025b3116727c56e567ce6a66f231`
- `data\interim\sih_morbidity_2018_2026.csv` — SHA-256 `be0c3911479f5635ddbbf91130a0686f391b145a5086ec1ba3b7c941480ae747`
- `data\interim\sih_morbidity_2024_2024.csv` — SHA-256 `77038aa2aa0b531fbe39f27b270d73cf14a6871df2c7eb8a39bd0d15a112b705`

A ausência de dados de idade/sexo no SIH impede taxas específicas neste produto; as taxas específicas SIM 2022 são um produto separado. Nenhuma associação ecológica é atribuída à CSN.
