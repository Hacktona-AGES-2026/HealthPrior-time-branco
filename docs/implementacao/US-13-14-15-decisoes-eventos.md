# US-13/14 · Decisão do regulador e US-15 · Evento novo — registro de implementação

> **Branch:** `feat/US-13-14-15-decisoes-eventos` · **Data:** 24/10/2026 · **Status:** implementado (329 testes sem banco passando; testes de banco rodam no CI). Sem coluna nova.

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

## Toda classe sugerida passa por um profissional (I-04, C-08)
Classe efetiva na fila: `classe_medico` → `classe_confirmada` (se confirmada) → **`classe_vigente`** → SWALIS.
- O SWALIS só vale direto para quem nunca teve mudança desde a carga (exceção D-01).
- Quando um evento muda a classe sugerida de quem **não** foi confirmado, a classe anterior fica **congelada** em `classe_vigente` (coluna `solicitacoes.classe_sistema`, que não era usada) e o paciente vai ao inbox; qualquer diferença sugerida × vigente entra no inbox.
- Para quem já foi confirmado, a fila usa a confirmada até nova decisão.
- Qualquer decisão descongela.
- O % do prazo segue a classe efetiva. `score_medico` envelhece a partir de `editado_em`, que é a **data de referência** (REF) da edição, nunca o relógio; o horário real fica no log `decisoes`.

## Cena da demo (resolvida pela D-97)
O SWALIS passou a usar a piora na espera (Q-SW2): um PS novo para SOL-2023-00060 sobe a classe de D para B, o desfecho é `enviado_inbox`, o regulador aprova e o paciente sobe na fila (coberto em `test_cena_da_demo_ps_vai_ao_inbox_aprova_e_o_paciente_sobe`). A biópsia positiva em paciente benigno (ex.: SOL-2026-00239, B → A2) continua valendo como segunda cena.
