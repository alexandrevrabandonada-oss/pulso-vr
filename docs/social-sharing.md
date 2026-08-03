# Compartilhamento social

A camada social publica apenas dados já presentes nos artefatos públicos do portal. URLs de `/compartilhar` aceitam identificadores validados de município, indicador, período, métrica, modelo e formato; títulos e textos livres não são aceitos.

## Superfícies

- `answer`: resposta municipal, período, métrica e status;
- `evolution`: minissérie que interrompe o traço em lacunas;
- `map`: contexto estadual com o município identificado;
- `og`, `feed` e `story`: 1200×630, 1080×1350 e 1080×1920.

O HTML social é servido por `/compartilhar` e a imagem por `/api/share-card`. O navegador humano retorna à rota canônica. WhatsApp e Facebook recebem a URL social; Instagram usa Web Share com arquivo quando disponível e download como fallback.

## Salvaguardas

- células suprimidas ou indisponíveis mostram somente “Dado protegido ou indisponível”;
- nenhuma função consulta dados internos não suprimidos;
- lacunas não são interpoladas;
- métrica, fonte, período e base territorial aparecem no card;
- o texto epidemiológico não é editável;
- a chave de cache inclui a release enviada pelo cliente;
- telemetria registra apenas superfície, modelo, formato e destino.

A release permanece em preview até inspeção dos cards nos validadores reais de Open Graph/Facebook e revisão epidemiológica do texto.
