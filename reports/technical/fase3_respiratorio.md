# Fase 3 — primeira série respiratória do SIH

Execução: 2026-08-03T01:37:30+00:00

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
| asthma | rest_of_rj_excluding_vr | 77254 |
| asthma | rj_total | 79150 |
| asthma | volta_redonda | 1896 |
| copd | rest_of_rj_excluding_vr | 80954 |
| copd | rj_total | 82711 |
| copd | volta_redonda | 1757 |
| pneumoconiosis | rest_of_rj_excluding_vr | 758 |
| pneumoconiosis | rj_total | 779 |
| pneumoconiosis | volta_redonda | 21 |
| pneumonia | rest_of_rj_excluding_vr | 645483 |
| pneumonia | rj_total | 659697 |
| pneumonia | volta_redonda | 14214 |
| resp_all | rest_of_rj_excluding_vr | 1111987 |
| resp_all | rj_total | 1140191 |
| resp_all | volta_redonda | 28204 |

## Arquivos intermediários usados

| arquivo | SHA-256 | linhas lidas |
| --- | --- | --- |
| data\interim\sih_morbidity_2008_2017.csv | fac4ff0a020d6717230b77c3617400d4995496677f15cb8536c6e20877d1aaa8 | 2160 |
| data\interim\sih_morbidity_2018_2026.csv | 4d82442080e1c5fa0a994766b7efcbdfee3e01a76d830a30321bcc16a0e0a5e5 | 1818 |
| data\interim\sih_morbidity_2024_2024.csv | 77038aa2aa0b531fbe39f27b270d73cf14a6871df2c7eb8a39bd0d15a112b705 | 18 |

## Limites para a análise seguinte

- A Lista Morb é uma agregação oficial do TabNet; o dicionário CID e a reconciliação com totais independentes ainda devem ser fechados.
- O denominador populacional agregado já pode ser integrado; taxas específicas do SIH exigem uma extração com idade/sexo, que não está nesta Lista Morb agregada.
- SIH é uma contagem de internações/AIH e não deve ser interpretado como número de indivíduos.
- 2025–2026-05 permanece provisório conforme a atualização do TabNet.
