# Multiplicador de idade e mortalidade

## Objetivo

Adicionar um contexto de mortalidade histórica nacional por CID e faixa etária
sem transformar esse contexto em probabilidade individual de óbito.

```text
CID principal + idade
        ↓
CID-3 + faixa etária
        ↓
IRR histórico nacional
        ↓
multiplicador de 1,00 a 1,15
```

## Fonte da referência

`references/irr_nacional_cid_idade_2019_2023.parquet` é a tabela de consulta
versionada nesta pasta. Ela foi produzida a partir de:

| Insumo | Período | Uso |
| --- | --- | --- |
| SIM / Ministério da Saúde | 2019–2023 | Óbitos cuja `CAUSABAS` é o CID da causa básica. |
| Projeções populacionais IBGE, revisão 2024 | 2019–2023 | População brasileira por idade; denominador das taxas. |

O CID é normalizado para três caracteres (`C50.4` → `C50`). As faixas são
`0–17`, `18–39`, `40–49`, `50–59`, `60–69`, `70–79` e `80+`.

## IRR

```text
IRR = taxa de mortalidade do CID na faixa etária
      ──────────────────────────────────────────
      taxa média nacional do mesmo CID, em todas as idades
```

Exemplo: `IRR = 2,00` indica que a taxa histórica daquele CID e faixa foi duas
vezes a taxa média nacional do mesmo CID. Não indica que um paciente tem duas
vezes mais chance individual de morrer.

## Conversão para fator

| Situação | Multiplicador | Regra gravada |
| --- | ---: | --- |
| IRR nulo, zero ou até 1,00 | 1,00 | Regra neutra |
| IRR acima de 1,00 | `1 + 0,075 × min(log2(IRR), 2)` | Ajuste gradual |
| Resultado máximo | 1,15 | Teto do fator |

Exemplo: `IRR = 3,93` produz aproximadamente `1,148`. Um IRR muito alto não
passa de `1,15`.

## Saída

| Coluna | Significado |
| --- | --- |
| `cid_3` | CID consultado após normalização. |
| `faixa_idade` | Faixa consultada. |
| `irr_contextual` | IRR histórico de referência. |
| `multiplicador_idade_mortalidade` | Fator limitado para composição futura. |
| `regra_multiplicador_idade_mortalidade` | Regra que definiu o fator. |
| `motivo_indisponibilidade` | Explica quando não há referência para o CID. |

Quando o CID não teve nenhum óbito como causa básica em 2019–2023, não existe
IRR matematicamente definido. O módulo registra o motivo e retorna o fator
neutro `1,00`.
