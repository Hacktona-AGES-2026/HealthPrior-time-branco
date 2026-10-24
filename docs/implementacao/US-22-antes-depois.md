# US-22 · Antes × depois — registro de implementação

> **Branch:** `feat/US-22-antes-depois` · **Data:** 24/10/2026 · **Status:** implementado (255 testes passando; banco pula sem Postgres)

## O que foi entregue
| Entrega | Arquivo |
|---|---|
| Métricas puras (definição do verificador oficial) | `backend/app/domain/metricas.py` |
| Caso de uso `CompararFilas` | `backend/app/application/comparar_filas.py` |
| `GET /metricas/comparacao` | `backend/app/api/routers/metricas.py`, schemas `IndicadoresOut`/`DestaqueOut`/`ComparacaoOut`, `get_comparar_filas` |
| Testes (inclui conferência com o verificador sobre o dataset real) | `tests/domain/test_metricas.py`, `tests/application/test_comparar_filas.py`, `tests/infrastructure/test_comparar_filas_dataset.py` |

```bash
curl localhost:8000/metricas/comparacao
```

## Como funciona
- **Antes** = ordem de hoje: prioridade manual (alta → média → baixa → vazia/desconhecida), depois data de entrada mais antiga, depois `solicitacao_id`. Todas as 941 solicitações.
- **Depois** = fila publicada (US-10). Sem publicação: `depois = null`, `publicada = false`.
- **Indicadores** (mesmas definições do verificador oficial): violações da regra de ouro (oncológicos abaixo do primeiro "sem urgência"), posição mediana dos oncológicos, % oncológicos no 1º terço, % com PS/internação nos últimos 180 dias na 1ª metade, % "sem urgência" no último terço.
- **Destaques**: posição antes/depois e camada de SOL-2023-00010, SOL-2025-00048, SOL-2026-00637, SOL-2026-00757, SOL-2023-00060.

### Números do "antes" no dataset real (conferidos contra o verificador)
| Indicador | Antes |
|---|---|
| Violações da regra de ouro | **177** (primeiro "sem urgência" na posição 12) |
| Posição mediana dos oncológicos | **287** de 941 |
| Oncológicos no 1º terço | 53,1% |
| PS/internação recente na 1ª metade | 37,5% |
| "Sem urgência" no último terço | 49,4% |

O "depois" depende da fila publicada no banco (rodar `python -m app.cli gerar-fila`); com o SWALIS atual a regra de ouro fica em **0 violações** (garantido pelo verificador na publicação).

## Decisões
| ID | Decisão | Motivo |
|---|---|---|
| D-59 | Indicadores com **exatamente a definição do verificador oficial** ("sem urgência" conta eventos em qualquer data, inclusive histórico e duplicados), com teste que confere o "antes" contra o próprio verificador | Números do pitch auditáveis pela banca |
| D-60 | Fila "antes" = prioridade manual (alta → média → baixa → vazia/desconhecida) + data de entrada + id | Reproduz a regra de hoje descrita no desafio; desconhecida junto da vazia (coerente com a normalização da US-02) |
| D-61 | Sem fila publicada, `depois = null` e `publicada = false` (200, não erro) | Mesmo padrão do `GET /fila` (D-56) |
| D-62 | Destaques padrão definidos na composição (`DESTAQUES_PADRAO` em `api/deps.py`) | Trocar os pacientes da demo sem mexer em regra |

Menores (subagente, revisadas pelo lead): no "depois", os conjuntos (oncológico, sem urgência, PS recente) são os mesmos do "antes", restritos aos IDs publicados; `posicao_antes` pode ser `null` para ID inexistente; mediana em `float` (o teste compara com o verificador com tolerância de 0,5, porque ele imprime inteiro).
