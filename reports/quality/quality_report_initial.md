# Relatório inicial de qualidade

Execução: 2026-08-02T19:22:00+00:00

## Escopo

Esta execução valida a estrutura, metadados, proveniência e amostras iniciais. Não calcula estimativas epidemiológicas.

## Arquivos brutos

Arquivos brutos não auxiliares encontrados: **8**.
Todos os arquivos brutos presentes devem ter sidecar `.sha256`.

## Log de extração

Entradas no log: **10**.
Contagem por status: `{"complete": 1, "downloaded": 8, "failed": 1}`.

## Achados e limites

- O workspace inicial não continha dados ou documentação; a Fase 2 agora possui amostras oficiais versionadas por hash.
- O endpoint FTP legado do SIH falhou na checagem de conectividade, mas a rota TabNet por residência foi executada para janeiro de 2024.
- O catálogo dinâmico de recursos SIM/SIVEP e os layouts observados foram preservados em metadata/.
- A reconciliação de totais oficiais ainda não foi executada.
- Não há resultado negativo ou positivo sobre saúde de Volta Redonda nesta fase.
