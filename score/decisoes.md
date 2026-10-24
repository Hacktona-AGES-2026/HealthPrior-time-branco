# Decisões — multiplicadores de score

Este documento registra as decisões adotadas para os dois fatores desta pasta:

```text
multiplicador_idade_mortalidade
multiplicador_comorbidade
```

Eles são fatores contextuais e auditáveis. Não constituem probabilidade
individual de óbito, regra clínica validada ou mecanismo de ordenação da fila.

| ID | Decisão | Motivo | Consequência |
| --- | --- | --- | --- |
| D-01 | Manter dois multiplicadores separados | Idade/mortalidade e carga de comorbidade representam sinais diferentes e precisam ser auditáveis separadamente | Cada solicitação recebe campos, explicações e regras independentes para os dois fatores |
| D-02 | Nomear o primeiro fator como `idade_mortality_multiplier` | O fator não é mortalidade individual: ele é derivado de CID e faixa etária | Evita confusão com o multiplicador de comorbidade e deixa explícita a participação da idade |
| D-03 | Usar IRR nacional por `CID-3 × faixa etária` | Há volume nacional suficiente; usar UF ou município deixaria muitas células instáveis | A referência usa Brasil inteiro, anos 2019–2023, sem UF ou município |
| D-04 | Usar SIM como numerador e IBGE como denominador | Contagem de óbitos sem população não é taxa comparável entre idades | O IRR é calculado por taxas de mortalidade, não por números brutos de óbitos |
| D-05 | Usar `CAUSABAS` do SIM | É o CID da causa básica do óbito e responde à pergunta de mortalidade por causa | O indicador não mede todas as causas associadas, letalidade de diagnosticados nem morte em fila |
| D-06 | Normalizar CID para três caracteres | `C50.4`, por exemplo, teria volume menor e maior instabilidade que `C50` | A consulta de mortalidade usa `cid_3`; o CID original é preservado na fila |
| D-07 | Usar sete faixas de idade | Faixas amplas são interpretáveis e dão volume suficiente para o período | `0–17`, `18–39`, `40–49`, `50–59`, `60–69`, `70–79`, `80+` |
| D-08 | Não usar sexo no multiplicador de idade e mortalidade | Foi escolhido para simplificar o fator e evitar uma camada demográfica adicional no score | O IRR atual depende somente de CID e faixa etária |
| D-09 | Não aplicar limiar mínimo de óbitos | O objetivo do hackathon é retornar valor para todos os CIDs e faixas possíveis | Células com poucos óbitos permanecem instáveis e devem ser apresentadas como contexto exploratório |
| D-10 | Tratar célula sem óbito como IRR 0 | A estimativa observada da taxa da célula é zero | O fator final é neutro, não reduz prioridade por ausência de óbito observado |
| D-11 | Tratar CID sem nenhum óbito no período como IRR indisponível | A razão `0 / 0` não é definida: não existe taxa média do CID para comparar | O motivo é registrado como `sem_obitos_para_o_cid_no_periodo` e o fator final é 1,00 |
| D-12 | Converter IRR em fator limitado de 1,00 a 1,15 | Multiplicar o score pelo IRR bruto poderia aumentar o score em várias vezes | Para IRR acima de 1: `1 + 0,075 × min(log2(IRR), 2)`; para IRR nulo, zero ou até 1: 1,00 |
| D-13 | Não reduzir score para IRR até 1 | Taxa abaixo da referência populacional não é evidência de menor necessidade individual | O fator de idade e mortalidade só aumenta de forma limitada ou fica neutro |
| D-14 | Usar Charlson sem idade para comorbidade | Idade já está no IRR; usar Charlson ajustado por idade duplicaria seu efeito | A coluna é `charlson_sem_idade`, nunca `charlson_ajustado_idade` |
| D-15 | Excluir `cid_principal` do Charlson | Em geral ele é a condição que motivou a cirurgia, não uma doença coexistente | Evita contar a indicação cirúrgica como comorbidade; somente texto de comorbidades e CID secundário são usados |
| D-16 | Aceitar texto de comorbidades e CID secundário | A fila não traz uma lista completa de diagnósticos estruturados de internação | O módulo preserva categorias e fontes detectadas para revisão; a cobertura é parcial |
| D-17 | Contar uma categoria Charlson apenas uma vez | A mesma doença pode aparecer no texto e no CID secundário | Evita duplicar pontos por uma única condição clínica |
| D-18 | Converter Charlson em faixas limitadas | Pesos originais do Charlson não são multiplicadores de prioridade | Charlson 0→1,00; 1→1,03; 2→1,06; 3–4→1,10; 5+→1,15 |
| D-19 | Não usar Elixhauser como multiplicador da fila | Alguns pesos van Walraven são negativos e o índice foi desenvolvido para outro contexto de mortalidade hospitalar | Elixhauser pode continuar como informação descritiva, mas não entra no fator desta pasta |
| D-20 | Manter o fator de comorbidade neutro para Charlson 0 | Ausência de categorias detectadas não comprova ausência de risco | Nenhuma solicitação recebe desconto no score por falta de evidência |
| D-21 | Não alterar `score_sistema`, classe ou posição | As regras do projeto reservam a ordenação ao SWALIS e suas camadas de segurança | Os módulos apenas produzem saídas em `data/processed/`; integração requer decisão explícita |
| D-22 | Tratar composição com JEV como proposta experimental | O JEV/LLM documentado no projeto deve apenas gerar alertas, não decidir classe ou score | A fórmula com JEV está no README como contrato futuro, não é executada por estes módulos |
| D-23 | Exigir score JEV relativo, de 0 a 100, para multiplicação direta | Multiplicar probabilidades pode exceder 1 e perder interpretação probabilística | Se o JEV retornar probabilidade, a combinação deve ser em log-odds e calibrada com desfechos |
| D-24 | Limitar impacto combinado por fator, não pelo IRR/Charlson bruto | Evita que uma associação populacional ou um índice de comorbidade domine o score principal | Cada fator fica entre 1,00 e 1,15; a combinação dos dois ainda requer análise de sensibilidade |

## Fórmula de composição proposta

Esta fórmula **não está conectada à ordenação da fila**. Ela descreve como os
fatores poderão ser combinados caso o time aprove um score externo JEV com
faixa 0–100:

```text
score_proposto = min(
  100,
  score_jev
  × multiplicador_comorbidade
  × multiplicador_idade_mortalidade
)
```

Exemplo:

```text
score_jev = 72
multiplicador_comorbidade = 1,06
multiplicador_idade_mortalidade = 1,148

score_proposto = min(100, 72 × 1,06 × 1,148) = 87,64
```

## Auditoria produzida pelos módulos

| Fator | Campos de auditoria |
| --- | --- |
| Idade e mortalidade | `cid_3`, `faixa_idade`, `irr_contextual`, `motivo_indisponibilidade`, `multiplicador_idade_mortalidade`, `regra_multiplicador_idade_mortalidade` |
| Comorbidade | `categorias_charlson_comorbidade`, `fontes_categorias_charlson`, `charlson_sem_idade`, `multiplicador_comorbidade`, `regra_multiplicador_comorbidade` |

## Limites que permanecem abertos

- Os percentuais e tetos dos multiplicadores são regras de produto, não pesos
  calibrados com desfechos locais.
- O SIM descreve mortalidade populacional histórica, não óbito durante a espera
  nem causalidade individual.
- O mapeamento de comorbidades por texto livre deve passar por revisão clínica.
- Antes de integrar ao score, deve-se simular impacto no ranking, observar a
  distribuição dos aumentos e validar se não há dupla contagem com as variáveis
  já usadas pelo JEV/SWALIS.
