# Portal Observatório Saúde & Ambiente

Frontend estático React/Vite. Ele não consulta dados pessoais nem um backend:
todos os números exibidos vêm dos artefatos auditáveis em `public/data/`,
gerados pelo comando Python `portal-data` na raiz do repositório.

```text
npm install
npm run dev
npm test
npm run lint
npm run build
npm run preview
```

## Hospedagem estática

As rotas são de uma SPA e precisam retornar `index.html` quando não apontam
para um arquivo real. `public/_redirects` prepara Cloudflare Pages e Netlify;
`vercel.json` aplica a mesma regra na Vercel, cuja resolução de `rewrites`
preserva arquivos estáticos existentes antes do fallback da SPA.

A pasta publicável é `dist/`. A implantação pública permanece bloqueada até a
aprovação epidemiológica, de acessibilidade, proveniência e supressão descrita
em `public/data/release.json`.

## Marca e SEO

O portal apresenta Observatório Estadual de Saúde do RJ e VR Abandonada como
realização conjunta. A parceria institucional não substitui as fontes
epidemiológicas exibidas pelos indicadores.

As páginas públicas recebem título, descrição, canonical, Open Graph, Twitter
Card e JSON-LD por rota. `robots.txt` e `sitemap.xml` são gerados pelas funções
Vercel conforme o status da release. Em beta técnica, a indexação permanece
bloqueada.
