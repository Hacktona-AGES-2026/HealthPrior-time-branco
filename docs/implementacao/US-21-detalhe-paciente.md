# US-21 · "Por que este paciente está aqui?" — registro de implementação

> **Branch:** `feat/US-21-detalhe-paciente` · **Data:** 24/10/2026 · **Status:** implementado (302 testes passando; banco pula sem Postgres)

## O que foi entregue
| Entrega | Arquivo |
|---|---|
| Explicação em texto e motivo da camada (funções puras) | `backend/app/domain/explicacao.py` |
| Caso de uso `DetalharSolicitacao` | `backend/app/application/detalhar_solicitacao.py` |
| `GET /solicitacoes/{id}` real (404 `SOLICITACAO_NAO_ENCONTRADA`) | `backend/app/api/routers/solicitacoes.py`, `get_detalhar_solicitacao` |
| `SqlPendenciaRepository.listar_por_solicitacao`; `SqlSolicitacaoRepository.obter`; `SqlCorrecaoRepository.listar_por_solicitacao` | `backend/app/infrastructure/repositories.py`, porta em `ports.py` |
| Testes | `tests/domain/test_explicacao.py`, `tests/application/test_detalhar_solicitacao.py`, `tests/api/test_solicitacao_detalhe.py` |

Exemplo de `explicacao`:
> Posição 1: oncológico pelo CID C18.7 (camada 1). Classe A2 (editada manualmente por Silas); prazo de 21 dias, 1318 dias em fila (6276.2% do prazo). Principais sinais: progressão 3: biópsia positiva; sintoma 2: dor EVA 8.

## Como funciona
- **Posição, camada e justificativa** vêm da **fila publicada** (a mesma do `GET /fila` e do CSV). Não publicado → posição/camada nulas e a explicação diz que ainda não está na fila publicada.
- **Score e motivos** vêm do **SWALIS na hora da consulta** (só cache do LLM, reproduzível), com a evidência de cada motivo.
- Eventos (com `historico` e `duplicado` marcados), correções automáticas e pendências da solicitação. Decisões do regulador ficam vazias até a US-13.

## Decisões
| ID | Decisão | Motivo |
|---|---|---|
| D-68 | Posição/camada da fila publicada; score e motivos do SWALIS calculados na leitura | A tela bate com a fila entregue e mostra a evidência atual |
| D-69 | Explicação montada por função pura do domínio (2 a 4 frases: posição e camada; classe, prazo, dias e %; até 3 motivos; edição manual; suspensão) | Testável e igual em qualquer tela; critério de explicabilidade (20%) |
| D-70 | Com `classe_medico`, prazo e % do prazo são recalculados pela classe decidida | Mesma regra de `montar_fila`: detalhe e fila mostram o mesmo número |

Menores (subagente, revisadas pelo lead): motivos na ordem do SWALIS, corte nos 3 primeiros (sem critério de relevância inventado); `camada_motivo` = "Oncológico pelo CID X" na camada 1 e a primeira frase da justificativa publicada nas demais; implementados `SqlSolicitacaoRepository.obter` e `SqlCorrecaoRepository.listar_por_solicitacao`, que estavam pendentes (**atenção no merge** com quem também mexer neles).
