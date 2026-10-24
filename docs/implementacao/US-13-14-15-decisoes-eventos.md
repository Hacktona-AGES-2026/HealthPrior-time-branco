# US-13/14 · Decisão do regulador e US-15 · Evento novo — registro de implementação

> **Branch:** `feat/US-13-14-15-decisoes-eventos` · **Data:** 24/10/2026 · **Status:** implementado (321 testes sem banco passando; testes de banco rodam no CI). Sem coluna nova.

## O que foi entregue
| Entrega | Arquivo |
|---|---|
| Regras da decisão (puras) | `backend/app/domain/decisao.py` |
| `DecidirClasse` (aprovar / editar / manter) | `backend/app/application/decidir.py` |
| `RegistrarEvento` | `backend/app/application/registrar_evento.py` |
| Classe e score efetivos na fila | `backend/app/application/montar_fila.py` (`classe_e_score_efetivos`) |
| `SqlDecisaoRepository`; `salvar` (solicitação), `adicionar` (evento), `salvar` (pendência nova) | `backend/app/infrastructure/repositories.py` |
| `POST /decisoes`, `POST /eventos` reais (mock só com `HP_USE_MOCKS=true`) | `routers/decisoes.py`, `routers/eventos.py`, `deps.py` |
| Testes | `tests/domain/test_decisao.py`, `tests/application/test_decidir_e_evento.py`, `tests/infrastructure/test_decisoes_eventos_banco.py` |

## US-13/14 · `POST /decisoes`
- **aprovar:** `classe_status = confirmada`, `classe_confirmada` = sugerida do SWALIS; desfaz override anterior (explícito).
- **editar:** classe e/ou score; grava `classe_medico`, `score_medico`, `editado_*`, `motivo_codificado`.
- **manter:** recusa a sugestão e fixa a classe atual (confirmada ou implícita da prioridade).
- `motivo_codificado` + `justificativa` obrigatórios em editar/manter (422 `JUSTIFICATIVA_OBRIGATORIA`); editar sem classe nem score → 422 `DECISAO_INVALIDA`; oncológico (CID C*) para C/D → 422 `ONCOLOGICO_REBAIXADO`.
- Grava a decisão no log (`decisoes`), confirma e **republica a fila pelo verificador** (`PublicarFila`). Se o verificador reprovar, a decisão fica e a fila anterior continua (`fila_publicada=false`). Resposta traz `posicao_anterior` e `posicao_nova`.

## US-15 · `POST /eventos`
Evento → PRE-07/08 (`marcar_eventos`) → PRE-06 (flags) → SWALIS antes × depois → desfecho:
- `pendencia`: contato com `desistiu` (PRE-23) ou `informou_cirurgia_outro_servico` (PRE-21) abre pendência bloqueante; o paciente **não** sai da fila sem humano (I-03).
- `enviado_inbox`: a classe sugerida mudou **e** o paciente entra na regra do inbox (US-12).
- `registrado`: só grava. A fila **não** é republicada (D-02): muda na próxima decisão/publicação.

## Classe efetiva na fila (C-10, C-08)
`classe_medico` → `classe_confirmada` (se confirmada) → SWALIS. O % do prazo segue a classe efetiva; `score_medico` envelhece a partir de `editado_em` no ritmo do prazo. Assim, depois de confirmado, um evento novo só muda a classe na fila após nova decisão.

## Limitação conhecida (cena da demo)
O SWALIS ainda **não usa eventos** (Q-SW2): um PS novo para SOL-2023-00060 não muda a classe (fica D), então o desfecho é `registrado`, não `enviado_inbox`. A camada muda (PS → camada 2) na próxima publicação. Para a cena "PS → inbox → aprova → sobe", o SWALIS precisa considerar eventos na espera (decisão pendente). Hoje dá para demonstrar com biópsia positiva em paciente benigno (ex.: SOL-2026-00239, C → A2 → inbox).
