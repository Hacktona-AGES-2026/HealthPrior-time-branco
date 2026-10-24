# US-20 · `GET /fila` real — registro de implementação

> **Branch:** `feat/US-20-fila-api` · **Data:** 24/10/2026 · **Status:** implementado (258 testes passando; banco pula sem Postgres)

## O que foi entregue
| Entrega | Arquivo |
|---|---|
| Caso de uso `ListarFila` (fila publicada + dados da solicitação, filtros, paginação) | `backend/app/application/listar_fila.py` |
| Rota `GET /fila` real (mock só com `HP_USE_MOCKS=true`) | `backend/app/api/routers/fila.py`, `get_listar_fila` em `api/deps.py` |
| `FilaOut.versao_regras` / `gerada_em` opcionais | `backend/app/api/schemas.py` |
| Testes | `tests/application/test_listar_fila.py`, `tests/api/test_fila_listar.py` |

```bash
curl "localhost:8000/fila?camada=1&page=1&page_size=20"
curl "localhost:8000/fila?especialidade=urologia&busca=SOL-2025"
```

## Como funciona
- Lê a **fila publicada** (`fila_publicada`, US-10) — nunca gera fila na leitura.
- Junta cada linha com a solicitação (procedimento, especialidade, CID, oncológico, alertas, `classe_status`).
- Filtros antes da paginação: `camada`, `procedimento_id`, `especialidade` (sem diferenciar maiúsculas), `busca` (parte do `solicitacao_id` ou `paciente_id`). `total` = após filtros. Ordem sempre pela posição publicada.

## Decisões
| ID | Decisão | Motivo |
|---|---|---|
| D-56 | Sem fila publicada, `GET /fila` responde **200** com `publicada: false` e lista vazia (não erro) | O front mostra "fila ainda não publicada" sem tratar exceção |
| D-57 | `GET /fila` lê **só a fila publicada** (a que passou no verificador), juntando com a solicitação para os campos de exibição | Ninguém vê fila reprovada; a ordem exibida é a mesma do CSV entregue |
| D-58 | Paginação: `page < 1` ou `page_size < 1` → **422 `PAGINACAO_INVALIDA`** (formato `{"erro","mensagem"}` do contrato); `page_size` acima de 200 é **limitado a 200** | Erros no formato padrão da API; limite protege a resposta sem quebrar o front |

Menores (subagente, revisadas pelo lead): `publicada` vem de `publicada_em()` (distingue "nunca publicada" de "publicada vazia"); procedimento/especialidade nulos viram `""`; linha publicada sem solicitação correspondente é ignorada. **Correção do lead:** o subagente validava paginação com `Query(ge/le)` (422 no formato padrão do FastAPI, fora do contrato); passou para o caso de uso, com corpo `PAGINACAO_INVALIDA`.
