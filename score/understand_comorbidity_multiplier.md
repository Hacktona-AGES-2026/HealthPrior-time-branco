# Multiplicador de comorbidade

## Objetivo

Resumir a carga de comorbidades em um fator limitado, sem contar novamente a
idade nem a doença que levou à indicação cirúrgica.

```text
comorbidades + CID secundário
             ↓
Charlson sem idade
             ↓
multiplicador de 1,00 a 1,15
```

## Entradas

| Campo da fila | Uso |
| --- | --- |
| `comorbidades` | Texto separado por `;`, usado para detectar condições conhecidas. |
| `cid_secundario` | Complementa a detecção quando há diagnóstico secundário codificado. |
| `cid_principal` | Não é usado: é a condição que motivou a cirurgia, não uma comorbidade. |
| `idade` | Não é usada: já é contemplada pelo fator de mortalidade. |

## Categorias e pontos

| Categoria Charlson | Exemplos reconhecidos | Pontos |
| --- | --- | ---: |
| Infarto/doença isquêmica | `cardiopatia isquemica`, `I21`, `I22`, `I25` | 1 |
| Insuficiência cardíaca | `icc`, `I50` | 1 |
| Doença pulmonar crônica | `dpoc`, `asma`, `J44`, `J45` | 1 |
| Diabetes sem complicação | `dm2`, `diabetes`, `E10`–`E14` | 1 |
| Doença renal | `drc`, `N18` | 2 |
| Tumor sólido secundário | CID secundário iniciado por `C` | 2 |
| Linfoma/leucemia secundário | `C81`–`C96` aplicáveis | 2 |
| Metástase secundária | `C77`–`C80` | 6 |

Categorias repetidas contam uma vez. Cada categoria e sua fonte são salvas nas
colunas `categorias_charlson_comorbidade` e
`fontes_categorias_charlson`.

## Conversão para fator

| Charlson sem idade | Multiplicador | Regra gravada |
| ---: | ---: | --- |
| 0 | 1,00 | `charlson_0` |
| 1 | 1,03 | `charlson_1` |
| 2 | 1,06 | `charlson_2` |
| 3–4 | 1,10 | `charlson_3_a_4` |
| 5 ou mais | 1,15 | `charlson_5_ou_mais` |

Exemplo: `DM2 + ICC + DRC` soma `1 + 1 + 2 = 4`; o multiplicador é `1,10`.

## Saída

| Coluna | Significado |
| --- | --- |
| `charlson_sem_idade` | Soma das categorias detectadas. |
| `multiplicador_comorbidade` | Fator limitado usado na composição futura. |
| `regra_multiplicador_comorbidade` | Faixa usada para gerar o fator. |
| `descricao_multiplicador_comorbidade` | Texto pronto para explicação. |

## Limites metodológicos

O Charlson foi criado como índice prognóstico com diagnósticos estruturados.
Neste dataset, parte da identificação vem de texto livre e a cobertura de
categorias é parcial. Por isso, este fator é contextual e auditável; ele não é
um risco clínico individual validado nem ordena a fila.
