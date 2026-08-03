# Lacunas de dados e plano de fechamento

Atualização: 2026-08-03

Este inventário separa o que a release pública aprovada mostra do que ainda
exige acompanhamento. Nenhuma lacuna é preenchida por interpolação ou
por média simples dos municípios.

## Cobertura liberada

| camada | cobertura atual | estado |
|---|---|---|
| SIM mortalidade agregada | Volta Redonda, RJ sem VR e Brasil; séries anuais elegíveis | disponível, com supressão `<5` |
| SIM perfis idade/sexo | Censo 2022, grupos amplos | disponível, somente 2022 |
| SIM mapa municipal | 92 municípios do RJ, 31 desfechos, ano 2022 | disponível, taxa bruta por residência |
| SIH comparador Brasil | NRBR oficial, por residência, 2008–2025 | integrado; estrutura validada |
| SIH mapa municipal | 92 municípios, 15 desfechos, snapshot 2022 | reconciliado e publicado |

## Lacunas que permanecem

1. **Ano sem denominador (aviso):** 2023 permanece como lacuna porque não há
   estimativa municipal oficial compatível disponível nesta aquisição. 2010 usa
   a população residente do Censo 2010 (SIDRA tabela 202). O frontend não
   transforma ausência em zero nem traça linha interpolada.
2. **Fontes futuras (aviso):** FTP legado do SIH, INMET, RHC e dados ocupacionais
   têm pendências de aquisição ou validação e não entram nos resultados atuais.
3. **Observações provisórias (aviso):** 2025 em SIH permanece rotulado como
   provisório; a data de atualização fica visível na proveniência.

## Critério de fechamento

O pré-voo só pode retornar `publicationAllowed=true` quando os dois portões de
revisão forem aprovados, o mapa SIH tiver valores municipais reconciliados (ou
for retirado explicitamente do escopo público) e todos os textos mantiverem a
distinção entre internações/AIHs, óbitos, notificações e registros assistenciais.
