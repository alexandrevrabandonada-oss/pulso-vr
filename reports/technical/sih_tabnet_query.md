# SIH/SUS — rota TabNet por residência

## Teste reproduzível

Em 2026-08-02, a definição oficial do SIH para o Rio de Janeiro foi lida em
`sih/cnv/nrrj`. O formulário expõe o município `330630 VOLTA REDONDA` com
valor interno `93` e o arquivo mensal `nrrj2401.dbf`. O pipeline enviou um POST
para `tabcgi.exe` com:

- linha: município;
- coluna: não ativa;
- conteúdo: internações;
- período: janeiro de 2024;
- filtro de residência: valor 93 de Volta Redonda;
- formato: pré-formatado (`prn`).

Resultado retornado pelo TabNet: **1.463 internações**. A resposta HTML bruta,
sem edição, está em `data/raw/sih_tabnet_nrrj_2024_01.html`, com sidecar SHA-256
e entrada em `metadata/extraction_log.csv`.

## Interpretação autorizada

Esse número é uma contagem agregada de internações/AIHs segundo residência,
não uma contagem de pessoas únicas. O mês é de processamento e geralmente se
aproxima do mês da alta, mas pode divergir em reapresentações, atrasos e longa
permanência. A página de notas técnicas também informa que transferências e
reinternações são computadas.

## Próxima expansão

Iterar os arquivos mensais `nrrjYYMM.dbf` de 2008 em diante, armazenar cada
resposta e extrair as linhas do município com um parser versionado. Antes de
liberar a série, comparar totais mensais/anuais com a tabulação oficial e
documentar mudanças no conjunto de períodos disponíveis.
