# DECISOES.md — HealthPrior (Time Branco)

Registro das decisões do time e das solicitações que ficaram fora do `fila_priorizada.csv`.
Decisões de fluxo detalhadas em `docs/fluxo-sistema.md` §10.

## Decisões

| ID | Data | Decisão | Motivo | Alternativa descartada | Componente |
|---|---|---|---|---|---|
| D-01 | 2026-10-24 | Carga inicial não passa pelo regulador; classe fica "sugerida, não confirmada" | Inviável revisar 941 casos | Regulador revisar tudo | C-02 |
| D-02 | 2026-10-24 | Evento sem mudança de classe só é registrado | Atualização diária já reordena; evita fadiga de alertas | Reordenar e notificar a cada evento | C-08 |
| D-03 | 2026-10-24 | Regulador edita classe ou score, não posição; flag `editado_manualmente` | Posição muda todo dia; score editado envelhece | Fixar posição | C-10 |
| D-04 | 2026-10-24 | Pré-processamento único para carga e eventos | Mesmas regras em lote e contínuo | Dois pipelines | C-05 |
| D-05 | 2026-10-24 | Inconsistências são sinalizadas, nunca apagadas | Auditabilidade | Remover registros | C-05, C-06 |
| D-06 | 2026-10-24 | Regra de ouro como camadas, não peso | Restrição dura | Peso alto no score | C-11 |
| D-07 | 2026-10-24 | Verificador é portão de publicação | Violação é eliminatória | Publicar e corrigir depois | C-12 |
| D-08 | 2026-10-24 | Aprendizado propõe regras; comitê aprova; versões | Controle humano | Retreino automático | C-14 |
| D-09 | 2026-10-24 | SWALIS interno documentado à parte | Separação de responsabilidades | — | C-07 |
| D-10 | 2026-10-24 | Duplicatas fundidas mantendo a data de entrada mais antiga | Favorece o paciente | Manter a mais recente | C-05 |
| D-11 | 2026-10-24 | Stack: FastAPI + pandas no back; React (Vite + TS) no front (banco: ver D-14) | Conhecimento do time; rapidez | — | todos |
| D-12 | 2026-10-24 | Sem login: seletor de persona e de usuário fixo no front | Hackathon; o log ainda registra autores distintos | Autenticação real | US-23 |
| D-13 | 2026-10-24 | API é a fronteira back × front; back sobe mocks com o contrato final primeiro | Trabalho em paralelo sem retrabalho | Front esperar o back | US-01..US-23 |
| D-14 | 2026-10-24 | Banco: PostgreSQL 16 (Docker) com SQLAlchemy 2, no lugar do SQLite | Banco de verdade para o pitch; concorrência (API + CLI) sem travar arquivo; upsert nativo para a carga idempotente | SQLite (simples, mas limitado para a demo); DuckDB (analítico, escrita de um processo só) | US-01 |
| D-15 | 2026-10-24 | Sem migrations (Alembic): tabelas criadas com `create_all`; mudança de schema = `docker compose down -v` e recarga | Hackathon; dados são reproduzíveis a partir dos CSVs | Alembic | US-01 |
| D-16 | 2026-10-24 | `eventos.solicitacao_id` sem chave estrangeira | Eventos órfãos existem no dataset e nada é apagado (I-03); a US-04 os sinaliza | FK (rejeitaria os órfãos na carga) | US-01 |
| D-17 | 2026-10-24 | `correcoes_log` registra mudanças de valor visíveis (município, prioridade, CID com minúscula/espaço). Chaves de comparação (`cid_norm` sem ponto, `nome_norm`) não geram log | 816 dos 941 CIDs têm ponto e quase todo nome difere só na caixa: ~1.700 linhas de ruído sem informação. O original fica sempre intacto na coluna de origem | Logar toda diferença entre original e `*_norm` (cumpre o CA "toda correção" ao pé da letra) | US-02 |
| D-18 | 2026-10-24 | `municipio_norm` usa o nome oficial do IBGE **com acento** (Gravataí, Osório, Viamão), via tabela fixa em `preprocessing.py` com os 38 municípios do dataset; município fora da tabela só perde espaços sobrando | PRE-03 pede o nome oficial; o dataset vem sem acento | Forma canônica sem acento (só unifica a caixa) | US-02 |
| D-19 | 2026-10-24 | A normalização roda dentro da carga (mesma transação) e também avulsa (`python -m app.cli normalizar`). Recalcula as colunas `*_norm` e refaz o log de PRE-01..04, sem tocar nas outras regras | D-04: mesmo pré-processamento para carga e eventos; evita carga sem normalizar | Só comando separado | US-02 |
| D-20 | 2026-10-24 | `nome_norm` = minúsculo, sem acento, espaços colapsados; prioridade desconhecida vira vazia e é registrada no log | PRE-02 e PRE-04 não definem o formato; é só chave de comparação | Maiúsculo; rejeitar a carga com prioridade inválida | US-02 |

## Solicitações fora da fila

> Preencher ao gerar a entrega. O verificador avisa quantas solicitações ficaram de fora; cada uma precisa de motivo.

| Motivo (regra) | Quantidade | Solicitações | Observação |
|---|---|---|---|
| Duplicata (PRE-20) | | | Mantida a de entrada mais antiga |
| Operou em outro serviço / convênio (PRE-21/22) | | | |
| Desistência (PRE-23) | | | |

## Premissas e limitações

- Dados 100% sintéticos; nenhum número aqui é evidência clínica.
- Pesos e prazos por procedimento são provisórios até validação com os mentores.
