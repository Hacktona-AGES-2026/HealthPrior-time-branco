# US-12 · Inbox do regulador — registro de implementação

> **Branch:** `feat/US-12-inbox` · **Data:** 24/10/2026 · **Status:** implementado (298 testes passando; banco pula sem Postgres)
> ⚠️ Coluna nova `solicitacoes.classe_confirmada`: recrie o banco (`docker compose down -v && docker compose up -d`, D-16).

## O que foi entregue
| Entrega | Arquivo |
|---|---|
| Regras do inbox (puras) | `backend/app/domain/inbox.py` |
| Caso de uso `ListarInbox` | `backend/app/application/listar_inbox.py` |
| `GET /inbox` real (mock só com `HP_USE_MOCKS=true`) | `backend/app/api/routers/inbox.py`, `get_listar_inbox` |
| Coluna `classe_confirmada` (preenchida pela US-13) | `tables.py`, `models.py`, `repositories.py` |
| Testes | `tests/domain/test_inbox.py`, `tests/application/test_listar_inbox.py`, `tests/infrastructure/test_inbox_dataset.py`, `tests/api/test_inbox.py` |

## Regra
Paciente **ativo e na fila publicada** entra no inbox quando:
- **nunca confirmado:** a classe sugerida pelo SWALIS diverge **2 ou mais níveis** da classe implícita da prioridade manual (alta→B, média→C, baixa/vazia→D), para cima ou para baixo;
- **já confirmado:** a classe sugerida é **diferente** da `classe_confirmada`.

Ordem: classe sugerida mais grave (A1 → D) → maior divergência → posição publicada. O inbox é **calculado na leitura** (SWALIS roda na hora, só com cache do LLM), sem tabela de propostas.

No dataset real: **296 itens** (273 sobem, 23 descem). SOL-2025-00048 (prioridade "baixa", SWALIS A2) está no inbox.

## Decisões
| ID | Decisão | Motivo |
|---|---|---|
| D-64 | Entra no inbox: nunca confirmado com divergência ≥ 2 níveis entre SWALIS e a classe implícita da prioridade manual; confirmado com qualquer mudança de classe | O inbox já nasce com os casos mais discrepantes para a demo e depois só recebe mudanças (escolha do time) |
| D-65 | Inbox calculado na leitura, sem tabela de propostas; `criado_em` = data da publicação | Nunca fica desatualizado; menos estado para a US-13/15 sincronizar (escolha do time) |
| D-66 | "Classe atual" do card = `classe_confirmada`, ou a classe implícita da prioridade manual se nunca confirmado. Nova coluna `classe_confirmada`, escrita pela US-13 | Referência explícita para a comparação |
| D-67 | Ordem: classe sugerida mais grave → maior divergência → posição publicada | Regulador vê primeiro quem o SWALIS quer subir para A1/A2 |

Menores (subagente, revisadas pelo lead): `criado_em` opcional (sem publicação); confirmado sem `classe_confirmada` é tratado como nunca confirmado; `evento_gatilho` = primeiro motivo de fonte "evento"; `regulador_id` aceito e ignorado (sem atribuição por regulador).
