# US-18 · Agrupar justificativas em propostas (C-14)

Branch `feat/US-18-aprendizado`. Decisões D-98..D-102 e D-106 em `DECISOES.md`.

## O que foi feito
| Camada | Arquivo | O quê |
|---|---|---|
| domain | `app/domain/aprendizado.py` | `ParametrosAprendizado`, `CasoAprendizado`, `PropostaRegra`, `direcao`, `proposta_id`, `agrupar` (puro: janela, volume, reguladores distintos, consistência, descarte I-01) |
| domain | `app/domain/ports.py` | `DecisaoRepository.listar_todas`, `ClassificadorMotivo`, `PropostaRepository` |
| application | `app/application/gerar_propostas.py` | `GerarPropostas`: monta casos (D-101), reclassifica `outro` (D-99), agrupa, grava (D-103) |
| application | `app/application/semear_aprendizado.py` | `SemearAprendizado`: 33 decisões sintéticas em 5 padrões (D-98) |
| application | `app/application/decidir.py` | a decisão passa a gravar `procedimento_id` |
| infrastructure | `tables.py`, `repositories.py` | `PropostaRegraTable`, `SqlPropostaRepository`, `listar_todas`; **removida a 2ª `SqlDecisaoRepository` duplicada** (sobra de merge, não gravava `procedimento_id`); `proximo_id` ignora `DEC-SEED-%` |
| infrastructure | `llm_motivos.py` | `ClassificadorMotivoLLM` (Jev/OpenRouter, cache próprio) |
| api | `routers/aprendizado.py`, `schemas.py`, `mocks.py`, `deps.py` (# US-18), `main.py` | `POST /aprendizado/gerar-propostas` |
| cli | `cli.py` | `seed-aprendizado`, `gerar-propostas` |

## Contrato
`POST /aprendizado/gerar-propostas` — corpo opcional `{min_casos?, min_reguladores?, janela_dias?, min_consistencia?}` (padrões Q-05; inválido → 422).
Resposta: `{analisadas, consideradas, outros_reclassificados, outros_sem_grupo, propostas: [PropostaRegraOut], descartadas: [PropostaRegraOut]}`.
`PropostaRegraOut`: `proposta_id, procedimento_id, procedimento, motivo, classe_de, classe_para, direcao (subir|rebaixar), n_casos, n_reguladores, consistencia, casos (decisao_ids), status (pendente|descartada), motivo_descarte`.

## Seed (padrões)
| Padrão | Procedimento | Motivo | Transição | Casos | Resultado |
|---|---|---|---|---|---|
| P1 | PROC004 colecistectomia | ps_recorrente | C→B | 8 editar (4 reg.) + 1 manter | proposta (consistência 0,89) |
| P2 | PROC002 herniorrafia inguinal | piora_funcional | D→C | 7 editar (3 reg.) + 2 `outro` | proposta; com LLM os 2 `outro` podem somar |
| P3 | PROC018 histerectomia | sugestao_exagerada | B→C | 6 editar (3 reg.) | **descartada (I-01)** |
| P4 | PROC006 safenectomia | dor_intensa | C→B | 4 editar (2 reg.) | barrada: volume/reguladores |
| P5 | PROC001 facectomia | dado_desatualizado | D→C | 5 editar (3 reg.), 120–150 dias atrás | barrada: janela |

## Validação
- `pytest`: 453 passed, 148 skipped (banco), 0 failed; `test_arquitetura` ok.
- Ponta a ponta (SQLite, sem LLM): `init-db → carga → seed-aprendizado → gerar-propostas` = 33 analisadas, 31 consideradas, 2 `outro` sem grupo, 2 pendentes (P1, P2) e 1 descartada (P3). Seed de novo = nada gravado. API real: mesmo resultado, nomes de procedimento preenchidos; `{"min_casos": 8}` deixa só P1; `min_consistencia: 2` → 422. Após o seed, `proximo_id` = `DEC-0001`.
- Não rodado no Postgres (sem Docker no ambiente do lead).

## Como rodar na demo
```bash
cd backend
python -m app.cli seed-aprendizado
python -m app.cli gerar-propostas   # ou POST /aprendizado/gerar-propostas
```

## Para a US-19
Ler `propostas_regra` com status `pendente`; `decidida_por/decidida_em/observacao` já existem na tabela. Casos de origem = `casos` (IDs de decisão, com justificativa no log).
