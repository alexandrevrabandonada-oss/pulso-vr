# Plano de aquisição e validação — SIH, SIM, IBGE e SIVEP

## Ordem operacional

1. Registrar landing page, recurso, versão, data de acesso e cobertura no
   catálogo.
2. Baixar sem edição para data/raw/ e criar SHA-256.
3. Validar integridade de container/JSON/Parquet/PDF e registrar falhas.
4. Inspecionar dicionário e detectar campos de residência, CID, idade, sexo,
   período e status de dados.
5. Normalizar layouts somente em data/interim/, preservando o bruto.
6. Produzir Parquet por fonte e ano.
7. Reconciliar totais agregados com TabNet, painéis ou documentação oficial.
8. Liberar análise somente com período, denominador e status de versão
   explícitos.

## SIH/SUS

Cobertura planejada: AIH reduzida de residentes no RJ, mês a mês, 2008–2026.

- Rota primária: página DATASUS de Transferência de Arquivos, fonte SIHSUS,
  modalidade Dados, tipo RD - AIH Reduzida.
- Rota alternativa: TabNet de Morbidade Hospitalar por local de residência e
  notas técnicas.
- Rota FTP legada testada em 2026-08-02: falhou por ausência de resposta do
  host. O resultado está em metadata/extraction_log.csv; não é convertido em
  zero nem em indisponibilidade definitiva.
- Validação: residência, código municipal/UF, mês de processamento, CID
  principal, sexo, faixa etária, permanência, UTI, valor e óbito. Comparar
  totais mensais/anuais de VR e RJ com tabulações oficiais.
- Limitações: cobertura SUS, AIH/reinternação, processamento que pode divergir
  da alta, longa permanência e mudanças de layout.

## SIM

Cobertura planejada: óbitos de residentes no RJ, 2010–2025 para câncer e
controles desde 2008 quando disponível.

- Rota primária: Portal de Dados Abertos do SUS, base SIM.
- Amostra adquirida: Mortalidade Geral 2024, ZIP oficial, íntegro, com
  DO24OPEN.csv e separador ;.
- Validação: dicionário, CODMUNRES, data, sexo, idade, causa básica e causas
  múltiplas; classificar ano como definitivo, preliminar ou prévia.
- Reconciliação: comparar contagens de residentes de VR e RJ com TabNet e
  painel oficial; causas múltiplas permanecem separadas da causa básica.
- Limitações: atraso de consolidação e revisão; 2025 em diante é provisório
  quando a fonte assim indicar.

## IBGE/SIDRA

Cobertura planejada: população anual e estrutura por idade/sexo de todos os
municípios do RJ.

- Rota de estrutura: SIDRA 9514, Censo 2022 por idade e sexo. A amostra de
  Volta Redonda foi baixada e validada como JSON com município 3306305, 2022
  e variável de população residente.
- Rota de denominador anual: SIDRA 6579, população residente estimada.
- Validação: código territorial, período, unidade, revisão da tabela e data
  de referência. A estrutura etária de 2022 não será tratada automaticamente
  como denominador de todos os anos.
- Limitações: estimativa anual tem referência em 1º de julho; taxas mensais
  exigem regra prévia de denominador médio ou anual.

## SIVEP-Gripe/SRAG

Cobertura planejada: 2019–2026, separando anos congelados e banco vivo.

- Rota primária: Portal de Dados Abertos do SUS, base SRAG 2019–2026.
- Amostras adquiridas: dicionário 2019–2025 e Parquet 2019.
- Validação: Parquet íntegro, 48.941 linhas, 194 colunas; presentes campos de
  município de notificação e residência, sexo, idade, início de sintomas,
  classificação final e evolução.
- Normalização: padronizar códigos de município, datas e classificações de
  vírus por versão do dicionário, sem comparar diretamente campos inexistentes
  em anos anteriores.
- Limitações: revisão contínua, subnotificação, mudanças de definição e
  vigilância ampliada na pandemia.

## Critério de liberação

Nenhum resultado principal será considerado liberado sem: arquivo bruto,
hash, catálogo, dicionário, teste de layout, reconciliação de total, status
definitivo/preliminar/provisório e nota de limitações.
