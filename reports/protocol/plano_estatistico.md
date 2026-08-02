# Plano estatístico preliminar

## Estimandos principais

1. Taxa de internação respiratória de residentes por 100 mil, por território,
   período, idade e sexo.
2. Razão de taxas e diferença de taxas entre Volta Redonda e o restante do RJ,
   com IC de Poisson.
3. Taxa de mortalidade por câncer por 100 mil, bruta, específica e diretamente
   padronizada pelo mesmo padrão etário.
4. Mudança de nível e tendência na série respiratória após março de 2020.
5. Associação entre poluição diária e eventos respiratórios em defasagens
   predefinidas, sem linguagem causal.

## Modelos

- Poisson/quasi-Poisson ou binomial negativa para contagens; offset no log do
  denominador populacional.
- Regressão segmentada para tendências anuais e mensais.
- Série temporal interrompida com março de 2020 como ruptura respiratória.
- GAM ou modelos de defasagem conforme diagnóstico de sobredispersão,
  autocorrelação e cobertura das séries ambientais.
- Mortalidade prematura e APVP com limite especificado antes da análise.
- FDR para desfechos secundários; resultados negativos serão reportados.

## Padronização

A população padrão será definida antes da análise final e usada em todos os
territórios. A escolha entre Censo 2022 e população brasileira padrão do Atlas
do INCA será justificada; as taxas não serão comparadas entre padrões distintos.

## Sensibilidades

- excluir 2020–2022 da linha de base respiratória;
- analisar 2020–2021 separadamente;
- usar causas básicas e múltiplas do SIM separadamente;
- restringir SIH a AIH de curta permanência quando o layout permitir;
- excluir meses/estações com cobertura ambiental abaixo do limiar pré-definido;
- comparar definição de residente e município de atendimento somente como
  análise de acesso, nunca como estimativa populacional de risco.
