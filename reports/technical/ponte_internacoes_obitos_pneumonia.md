# Ponte descritiva entre internações e óbitos por pneumonia

## Objetivo

Este relatório acrescenta uma leitura conjunta da série do Sistema de
Informações Hospitalares do SUS (SIH/SUS) e do Sistema de Informações sobre
Mortalidade (SIM) para residentes de Volta Redonda e para o restante do estado
do Rio de Janeiro, excluindo Volta Redonda.

O indicador apresentado é uma razão descritiva:

\[
\text{AIHs por óbito} = \frac{\text{internações/AIHs por pneumonia no ano}}
{\text{óbitos de residentes por pneumonia no ano}}
\]

Ele não é letalidade, não acompanha indivíduos e não deve ser interpretado
como número de internações por pessoa. Uma AIH é um evento administrativo e
pode incluir reinternação; o denominador do SIM é formado por óbitos de
residentes segundo a causa básica.

## Resultado principal

| Ano | VR: AIHs | VR: óbitos | VR: AIHs/óbito | Restante RJ: AIHs | Restante RJ: óbitos | Restante RJ: AIHs/óbito |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 640 | 140 | 4,6 | 30.937 | 9.644 | 3,2 |
| 2019 | 863 | 145 | 6,0 | 31.315 | 10.334 | 3,0 |
| 2020 | 469 | 120 | 3,9 | 25.917 | 9.557 | 2,7 |
| 2021 | 657 | 112 | 5,9 | 26.422 | 9.855 | 2,7 |
| 2022 | 851 | 123 | 6,9 | 40.457 | 10.192 | 4,0 |
| 2023 | 1.021 | 124 | 8,2 | 41.652 | 10.136 | 4,1 |
| 2024 | 1.303 | 153 | 8,5 | 41.434 | 11.889 | 3,5 |

Entre 2018 e 2024:

- em Volta Redonda, as AIHs aumentaram 103,6%, enquanto os óbitos cresceram
  9,3%;
- no restante do RJ, as AIHs aumentaram 33,9%, enquanto os óbitos cresceram
  23,3%;
- a razão AIHs/óbito de VR ficou acima da do restante do RJ em todos os anos
  observados, com diferença particularmente grande em 2023–2024;
- o comportamento de 2020–2021 deve ser lido à luz da ruptura respiratória da
  pandemia e da interrupção/alteração do acesso assistencial.

## Interpretação epidemiológica prudente

O achado fortalece a conclusão de que há uma dissociação entre carga
hospitalar e mortalidade por pneumonia em VR: o SIH mostra carga de internação
persistente e crescente, enquanto o SIM mostra mortalidade inferior à do
restante do RJ. O aumento da ponte AIHs/óbito é compatível com hipóteses como:

1. maior acesso ou concentração de atendimento hospitalar para residentes de
   VR;
2. maior frequência de reinternações ou de eventos administrativos por pessoa;
3. mudança de composição dos casos internados, com mais casos tratáveis ou
   menos graves;
4. diferenças de cobertura, codificação, transferência e fluxo regional;
5. alterações de diagnóstico e registro após a pandemia.

Essas hipóteses não são distinguíveis apenas com os agregados atuais. O
resultado não demonstra proteção, menor gravidade individual, qualidade
assistencial superior ou causalidade ambiental/ocupacional.

## O que a base atual permite afirmar

- O excesso de AIHs por 100 mil habitantes em VR é consistente na série e não
  parece concentrado em um único mês de 2024.
- A mortalidade por pneumonia em VR permanece abaixo do restante do RJ nos
  períodos agregados já avaliados.
- A razão AIHs/óbito é útil como sinal de mudança conjunta entre serviços e
  mortalidade, mas não substitui uma análise de pessoas, casos ou coortes.

## Auditoria necessária antes de concluir sobre o mecanismo

Para explicar a dissociação, a próxima etapa deve solicitar ou processar, sob
as regras de acesso e confidencialidade aplicáveis:

- município de residência e município/unidade de atendimento, separados;
- caráter da internação, diagnóstico principal e diagnósticos secundários;
- alta, transferência e óbito hospitalar;
- idade e sexo agregados, com supressão de células pequenas;
- identificador técnico anonimizado ou método de deduplicação para estimar
  pessoas e reinternações, se juridicamente disponível;
- reconciliação dos totais mensais com TabNet e com os arquivos brutos
  versionados.

## Fontes e limitações

- SIH/SUS: `data/interim/sih_morbidity_2018_2026.csv`; contagens agregadas de
  internações/AIHs por residência.
- SIM: `data/processed/outcome_counts_sim_sivep.parquet`; óbitos de residentes
  por causa básica.
- As duas fontes não formam uma coorte vinculada e possuem regras, coberturas
  e tempos de processamento diferentes.
- 2025 e 2026 permanecem fora deste quadro principal por serem provisórios ou
  incompletos; 2026 contém somente parte do ano.
- Nenhuma associação aqui autoriza atribuição causal à CSN ou à poluição.
