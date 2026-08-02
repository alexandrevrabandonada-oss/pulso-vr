# Relatório inicial de qualidade

Execução: 2026-08-02T20:30:09+00:00

## Escopo

Esta execução valida a estrutura, metadados, proveniência e amostras iniciais. Não calcula estimativas epidemiológicas.

## Arquivos brutos

Arquivos brutos não auxiliares encontrados: **67**.
Todos os arquivos brutos presentes devem ter sidecar `.sha256`.

## Log de extração

Entradas no log: **154**.
Contagem por status: `{"complete": 1, "downloaded": 67, "failed": 1, "skipped_existing_verified": 85}`.

## Achados e limites

- O workspace inicial não continha dados ou documentação; a Fase 2 agora possui amostras oficiais versionadas por hash.
- O endpoint FTP legado do SIH falhou na checagem de conectividade, mas a rota TabNet por residência foi executada para 60 meses entre 2020 e 2024.
- O catálogo dinâmico de recursos SIM/SIVEP e os layouts observados foram preservados em metadata/.
- A série SIH harmonizada em data/interim/ é descritiva e mantém o vínculo com cada resposta HTML bruta.
- A reconciliação de totais oficiais ainda não foi executada.
- Não há resultado negativo ou positivo sobre saúde de Volta Redonda nesta fase.
