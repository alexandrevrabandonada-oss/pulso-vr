# Profundidade territorial possível para câncer em Volta Redonda

Atualização: 2026-08-03

## Conclusão territorial

As bases públicas utilizadas nesta fase permitem analisar diagnósticos por
Brasil, estado, região, município da residência e, no Painel-Oncologia,
município do diagnóstico e do tratamento. Elas não permitem identificar de
forma validada o bairro de residência dos casos de câncer.

Portanto, ainda não é possível afirmar que um bairro de Volta Redonda tenha
mais diagnósticos ou maior risco de câncer do que outro.

## Auditoria das fontes

| fonte | maior detalhe territorial encontrado | permite bairro de residência? | uso atual |
|---|---|---|---|
| Painel-Oncologia | Brasil, UF, região, município de residência, município de diagnóstico e município de tratamento | não na consulta pública utilizada | casos registrados e fluxo assistencial |
| SIM público | município de residência e município de ocorrência | não no arquivo público harmonizado; o arquivo 2024 não contém `BAIRES` ou `bairro` | mortalidade |
| RHC/IntegradorRHC | hospital, município/região/UF, origem/procedência e variáveis clínicas | não no tabulador público utilizado | perfil hospitalar, estágio e tratamento |
| SIH/SUS | município de residência e município de atendimento | não na série pública usada | internações/AIH, não casos únicos |
| Prefeitura/IPPU | bairros, limites, logradouros, unidades e equipamentos | não há série pública de câncer por bairro localizada | denominadores territoriais, rede e contexto |

## Bairros encontrados nas ações de prevenção

Esses bairros devem ser interpretados como **territórios de intervenção ou
oferta**, e não como locais de maior ocorrência de câncer:

- O projeto-piloto inicial do Prevenir foi associado à área da UBSF Vila Mury,
  com cadastramento de famílias e 97 ruas.
- O Prevenir 50+ foi implantado inicialmente nas UBSFs de Água Limpa I,
  Siderlândia, Retiro I e Nova Primavera.
- A Secretaria informou ações de divulgação do programa no Siderlândia e
  expansão gradual para outras unidades.
- O endereço da LAO em Nossa Senhora das Graças identifica um serviço, não a
  residência dos pacientes.

As informações oficiais da Prefeitura descrevem programas, cobertura,
consultas, rastreamento e locais das UBSFs, mas não publicam uma tabela de
casos de câncer por bairro de residência. Ver fontes municipais ao final.

## O que falta para um mapa de bairros válido

O conjunto mínimo seria uma tabela agregada, sem nomes, CPF, endereço ou
identificador individual, contendo:

1. ano do diagnóstico;
2. bairro de residência padronizado pelo cadastro municipal;
3. grupo de câncer/CID-10 agregado;
4. faixa etária ampla e sexo;
5. estágio I–IV ou agrupamento equivalente;
6. diagnóstico, primeiro tratamento e intervalo até tratamento;
7. unidade de origem, UBSF de referência e município do tratamento;
8. população residente do bairro ou denominador por setor censitário;
9. versão dos limites dos bairros e regra para áreas sem bairro cadastrado.

Células com menos de cinco pessoas devem ser suprimidas ou agregadas. O
resultado deve ser publicado somente em tabela ou mapa agregado, nunca como
endereço ou ponto individual.

## Estratégia analítica quando a tabela for obtida

O estudo deverá comparar cada bairro com o conjunto de Volta Redonda e, em
segunda camada, com o restante do RJ e o Brasil. A análise deverá apresentar
contagens, taxas de registro, intervalos de incerteza quando apropriado,
completude, população denominadora, sensibilidade às mudanças de limite e
separação entre local de residência, local de diagnóstico e local de
tratamento.

Também será necessário distinguir duas perguntas diferentes:

- **onde os residentes moram:** análise territorial de risco populacional;
- **onde o sistema detecta e trata:** análise de acesso, encaminhamento e
  capacidade da rede.

Misturar essas duas geografias poderia fazer um bairro com hospital ou UBSF
parecer ter mais câncer apenas porque concentra atendimento.

## Fontes consultadas

- [Painel-Oncologia — Ministério da Saúde](https://www.gov.br/saude/pt-br/composicao/saes/cgcan/cgcan)
- [Painel TabNet — Oncologia](http://tabnet.datasus.gov.br/cgi/dhdat.exe?PAINEL_ONCO/PAINEL_ONCOLOGIABR.def)
- [RHC — INCA](https://www.inca.gov.br/en/numeros-de-cancer/registros-hospitalares-de-cancer-rhc)
- [Mapa Virtual de Volta Redonda](https://www2.voltaredonda.rj.gov.br/geo/index.php)
- [Caderno de Bairro — IPPU/Volta Redonda](https://www2.voltaredonda.rj.gov.br/ippu/mod/informacoes/caderno_bairro.php)
- [Programas municipais de prevenção e tratamento](https://www.voltaredonda.rj.gov.br/comunicacao/noticias/29-sms/11406-programas-municipais-de-preven%C3%A7%C3%A3o-e-tratamento-do-c%C3%A2ncer-salvam-centenas-de-vidas-em-volta-redonda)
- [Prevenir 50+ e UBSFs piloto](https://www.voltaredonda.rj.gov.br/comunicacao/noticias/29-sms/11766-equipe-da-linha-de-aten%C3%A7%C3%A3o-oncol%C3%B3gica-de-volta-redonda-divulga-prevenir-50-no-siderl%C3%A2ndia/)
