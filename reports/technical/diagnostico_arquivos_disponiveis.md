# Diagnóstico inicial de arquivos disponíveis

Data do diagnóstico: 2026-08-02

## Estado de entrada

O diretório compartilhado continha apenas um repositório Git sem commits e
nenhum arquivo de dados, documentação, credencial ou base anterior. O texto
anexado foi a única especificação recebida.

## Arquivos criados/adquiridos nesta execução

- Estrutura do projeto, configurações, protocolo e matriz de perguntas.
- data/raw/ibge_sidra_9514_vr_2022.json: resposta da API SIDRA 9514 para
  Volta Redonda em 2022; SHA-256 registrado.
- data/raw/sim_mortalidade_geral_2024_csv.zip: ZIP oficial do SIM 2024; ZIP
  íntegro, contendo DO24OPEN.csv separado por ponto e vírgula; SHA-256
  registrado.
- data/raw/sim_2010_Mortalidade_Geral_2010_csv.zip e
  data/raw/sim_2020_Mortalidade_Geral_2020_csv.zip: ZIPs oficiais descobertos
  pelo catálogo dinâmico do SIM; SHA-256 registrado.
- data/raw/sivep_srag_dicionario_2019_2025.pdf: dicionário oficial; cabeçalho
  PDF válido; SHA-256 registrado.
- data/raw/sivep_srag_2019_2026-03-23.parquet: amostra SIVEP 2019; 48.941
  linhas, 194 colunas e grupo de campos territoriais, sexo, idade, início de
  sintomas, classificação final e evolução presentes; SHA-256 registrado.
- data/raw/sivep_2020_INFLUD20-23-03-2026.parquet: amostra SIVEP 2020; 1.206.920
  linhas, 194 colunas e campos mínimos presentes; SHA-256 registrado.

## O que não foi encontrado/adquirido

Não foram adquiridos ainda os arquivos completos mensais do SIH/SUS, a série
completa do SIM, todos os anos do SIVEP, séries diárias de qualidade do ar e
meteorologia, RHC, SISCAN, Painel Oncologia, CNES histórico, cobertura de planos
privados ou dados ocupacionais.

O log registra que o FTP legado do SIH não respondeu neste ambiente. A página
oficial de transferência e o TabNet continuam documentados como rotas de
aquisição/reconciliação.
