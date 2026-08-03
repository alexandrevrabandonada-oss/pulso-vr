# Fase 3 — primeira série respiratória do SIH

Execução: 2026-08-03T03:02:02+00:00

## Escopo

Esta entrega tabula internações agregadas do SIH por município de residência, usando a Lista Morb CID-10 do TabNet. Volta Redonda é comparada ao total do RJ e ao restante do RJ calculado como total estadual menos VR.

O produto é descritivo e estrutural. Não representa pessoas únicas, casos novos, taxas, incidência, mortalidade, excesso ou causalidade.

## Cobertura e controle

- Competências observadas: **2008-01 a 2026-05** (221 meses).
- Competências ausentes dentro do intervalo: **0** (nenhuma).
- Linhas duplicadas removidas ao combinar janelas: **18**.
- Valores negativos: **0**.
- O símbolo `-` da legenda oficial do TabNet foi convertido para zero numérico, pois a própria legenda o define como zero não resultante de arredondamento.

## Soma dos eventos agregados por janela completa

| desfecho | território | internações agregadas |
| --- | --- | --- |
| acute_bronchitis_bronchiolitis | rest_of_rj_excluding_vr | 64797 |
| acute_bronchitis_bronchiolitis | rj_total | 66302 |
| acute_bronchitis_bronchiolitis | volta_redonda | 1505 |
| acute_myocardial_infarction | rest_of_rj_excluding_vr | 167003 |
| acute_myocardial_infarction | rj_total | 173065 |
| acute_myocardial_infarction | volta_redonda | 6062 |
| asthma | rest_of_rj_excluding_vr | 77254 |
| asthma | rj_total | 79150 |
| asthma | volta_redonda | 1896 |
| cardiac_arrhythmia | rest_of_rj_excluding_vr | 63861 |
| cardiac_arrhythmia | rj_total | 66186 |
| cardiac_arrhythmia | volta_redonda | 2325 |
| cardio_all | rest_of_rj_excluding_vr | 1337726 |
| cardio_all | rj_total | 1382430 |
| cardio_all | volta_redonda | 44704 |
| cerebrovascular | rest_of_rj_excluding_vr | 319213 |
| cerebrovascular | rj_total | 328944 |
| cerebrovascular | volta_redonda | 9731 |
| copd | rest_of_rj_excluding_vr | 80954 |
| copd | rj_total | 82711 |
| copd | volta_redonda | 1757 |
| heart_failure | rest_of_rj_excluding_vr | 246013 |
| heart_failure | rj_total | 255053 |
| heart_failure | volta_redonda | 9040 |
| hypertension | rest_of_rj_excluding_vr | 92328 |
| hypertension | rj_total | 93882 |
| hypertension | volta_redonda | 1554 |
| ischemic_heart_disease | rest_of_rj_excluding_vr | 318970 |
| ischemic_heart_disease | rj_total | 331011 |
| ischemic_heart_disease | volta_redonda | 12041 |
| pneumoconiosis | rest_of_rj_excluding_vr | 758 |
| pneumoconiosis | rj_total | 779 |
| pneumoconiosis | volta_redonda | 21 |
| pneumonia | rest_of_rj_excluding_vr | 645483 |
| pneumonia | rj_total | 659697 |
| pneumonia | volta_redonda | 14214 |
| pulmonary_embolism | rest_of_rj_excluding_vr | 6338 |
| pulmonary_embolism | rj_total | 6627 |
| pulmonary_embolism | volta_redonda | 289 |
| resp_all | rest_of_rj_excluding_vr | 1111987 |
| resp_all | rj_total | 1140191 |
| resp_all | volta_redonda | 28204 |

## Arquivos intermediários usados

| arquivo | SHA-256 | linhas lidas |
| --- | --- | --- |
| data\interim\sih_morbidity_2008_2017.csv | b28d4dfc8b7fb7aeca4a90a470e42f203c15025b3116727c56e567ce6a66f231 | 5040 |
| data\interim\sih_morbidity_2018_2026.csv | be0c3911479f5635ddbbf91130a0686f391b145a5086ec1ba3b7c941480ae747 | 4242 |
| data\interim\sih_morbidity_2024_2024.csv | 77038aa2aa0b531fbe39f27b270d73cf14a6871df2c7eb8a39bd0d15a112b705 | 18 |

## Limites para a análise seguinte

- A Lista Morb é uma agregação oficial do TabNet; o dicionário CID e a reconciliação com totais independentes ainda devem ser fechados.
- O denominador populacional agregado já pode ser integrado; taxas específicas do SIH exigem uma extração com idade/sexo, que não está nesta Lista Morb agregada.
- SIH é uma contagem de internações/AIH e não deve ser interpretado como número de indivíduos.
- 2025–2026-05 permanece provisório conforme a atualização do TabNet.
