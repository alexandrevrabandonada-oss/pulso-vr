# Marca institucional e SEO

## Co-branding

O Observatório Estadual de Saúde do RJ é o produto principal. Observatório e
VR Abandonada aparecem como **realização conjunta** no cabeçalho, nas páginas
públicas, na home, no rodapé e nos cards sociais.

VR Abandonada não é fonte epidemiológica. Cada número continua identificando
fonte, unidade, período, território, status, supressão e limitações.

O perfil institucional utilizado pelo portal é:

<https://www.instagram.com/vr_abandonada/>

## SEO

Os metadados por rota são gerados a partir do catálogo e dos artefatos públicos.
Páginas municipais, indicadores, métodos e dados podem ser indexadas somente
quando a release estiver liberada para publicação.

Enquanto `release.json` estiver em `technical_beta_not_for_public_release`:

- as páginas HTML usam `noindex,nofollow`;
- `robots.txt` bloqueia o rastreamento;
- `sitemap.xml` permanece vazio;
- APIs, dados brutos, compartilhamento e explorador técnico ficam fora do índice.

Quando a release pública for aprovada, `robots.txt` e `sitemap.xml` passam a
listar as páginas estáveis de cada domínio configurado. O projeto atualmente
mantém `pulsovr.online` e `pulsorj.online` indexáveis, decisão que exige
monitoramento de duplicidade e canonical no Search Console.

Valores protegidos, indisponíveis ou incompatíveis nunca entram em título,
descrição, JSON-LD, imagem social ou texto alternativo.
