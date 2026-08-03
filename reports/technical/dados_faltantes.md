# Lista objetiva de dados faltantes

## Bloqueiam as análises principais

- Reconciliação oficial dos arquivos SIH/SUS já coletados para residentes do
  RJ (2008–2025 e 2026 até maio), com dicionários, totais independentes e
  atualização dos meses ainda não publicados.
- SIM completo dos anos planejados, incluindo causas múltiplas quando
  publicamente disponíveis e indicação de definitivo/preliminar.
- População anual por município está disponível; 2010 usa o Censo 2010, mas
  2023 não tem denominador oficial compatível nesta aquisição; a estrutura compatível de idade/sexo
  existe para 2022, e ainda falta uma série completa para padronização temporal.
- SIVEP 2021–2026 foi adquirido em Parquet e harmonizado; 2026 é parcial na
  versão de 27/07/2026. Ainda falta a auditoria de versões/cobertura para
  comparação temporal completa.

## Necessários para pandemia e poluição

- Série diária por estação e poluente do INEA/Portal SIGQAR, com cobertura,
  flags e unidades.
- Meteorologia diária INMET ou estação oficial comparável para temperatura,
  umidade, chuva e vento.
- Vacinação por município e data, além de regras de população-alvo.
- Séries de influenza, VSR e outros vírus com mesma definição ao longo do
  tempo.

## Necessários para câncer e assistência

- RHC com cobertura por hospital/ano, estágio, ocupação, tabagismo e
  procedência, em forma agregada ou sob acordo seguro.
- Painel-Oncologia foi adquirido para Volta Redonda e RJ (2013–2024), com
  contagens por ano e diagnóstico detalhado. Ainda faltam dicionários,
  cobertura por fonte/unidade, completude, tratamento, intervalo diagnóstico-
  tratamento e registros acima de 60 dias; portanto a série atual é de
  registros diagnósticos assistenciais, não incidência populacional.
- SISCAN municipal agregado, com cobertura de rastreamento, exames alterados,
  confirmação e seguimento, para interpretar especialmente colo do útero e
  mama.
- CNES histórico de hospitais, leitos, UTI e habilitação oncológica.
- Produção ambulatorial/hospitalar e cobertura de planos privados para avaliar
  acesso fora do SUS.
- Diagnósticos e mortalidade agregados por bairro de residência, com limites
  territoriais e denominadores por bairro; as fontes públicas atuais chegam ao
  município e não permitem rankear bairros por câncer.

## Necessários para exposição ocupacional

- Histórico de trabalhadores, setores, ocupações, duração e matriz de
  exposição, em formato agregado inicialmente.
- Medições históricas de agentes e relatórios ambientais/ocupacionais.
- Documentos de vínculo, inclusão, comparação e latência que permitam
  protocolo aprovado, sem receber dados pessoais no repositório.
