# Síntese pandêmica do SIVEP

Execução: 2026-08-02T23:15:21+00:00

O SIVEP é uma base de vigilância de SRAG. As taxas abaixo são taxas de notificação por 100 mil residentes, não incidência, e dependem de cobertura, definição de caso, completude e atualização do sistema.

- Linhas agregadas: **15**.
- Anos disponíveis: **[2019, 2020]**.
- Anos sem denominador: **[]**.
- 2020 é marcado como período pandêmico; março de 2020 é a ruptura mensal definida no protocolo.
- Células menores que cinco são exibidas como `<5`.

## Notificações e óbitos entre notificações

| ano | território | desfecho | notificações | notificações/100 mil | óbitos | % óbitos/notificações |
|---:|---|---|---:|---:|---:|---:|
| 2019 | rest_of_rj_excluding_vr | influenza | 308 | 1.81 | 71 | 23.05 |
| 2019 | rj_total | influenza | 321 | 1.86 | 72 | 22.43 |
| 2019 | volta_redonda | influenza | 13 | 4.76 | <5 | 7.69 |
| 2019 | rest_of_rj_excluding_vr | srag | 2310 | 13.59 | 310 | 13.42 |
| 2019 | rj_total | srag | 2426 | 14.05 | 334 | 13.77 |
| 2019 | volta_redonda | srag | 116 | 42.49 | 24 | 20.69 |
| 2020 | rest_of_rj_excluding_vr | covid19 | 83968 | 491.26 | 34029 | 40.53 |
| 2020 | rj_total | covid19 | 84951 | 489.17 | 34467 | 40.57 |
| 2020 | volta_redonda | covid19 | 983 | 358.77 | 438 | 44.56 |
| 2020 | rest_of_rj_excluding_vr | influenza | 138 | 0.81 | 26 | 18.84 |
| 2020 | rj_total | influenza | 140 | 0.81 | 27 | 19.29 |
| 2020 | volta_redonda | influenza | <5 | 0.73 | <5 | 50.00 |
| 2020 | rest_of_rj_excluding_vr | srag | 122393 | 716.08 | 41025 | 33.52 |
| 2020 | rj_total | srag | 123918 | 713.56 | 41615 | 33.58 |
| 2020 | volta_redonda | srag | 1525 | 556.59 | 590 | 38.69 |

A proporção de óbitos é descritiva entre notificações com os códigos de evolução observados; não é letalidade populacional. Não há modelo de série temporal interrompida com apenas estes dois anos.

## Limitações

- 2019 e 2020 são arquivos SIVEP versionados, sujeitos a revisão e mudanças de cobertura.
- O comparador territorial usa residência e exclui Volta Redonda do restante do RJ.
- Não há ajuste por idade, sexo, vacinação, circulação viral, sazonalidade ou acesso.
- Nenhuma associação com poluição ou CSN é estimada nesta etapa.
