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
| D-11 | 2026-10-24 | Stack: FastAPI + pandas no back; React (Vite + TS) no front (banco: ver D-15) | Conhecimento do time; rapidez | — | todos |
| D-12 | 2026-10-24 | Sem login: seletor de persona e de usuário fixo no front | Hackathon; o log ainda registra autores distintos | Autenticação real | US-23 |
| D-13 | 2026-10-24 | API é a fronteira back × front; back sobe mocks com o contrato final primeiro | Trabalho em paralelo sem retrabalho | Front esperar o back | US-01..US-23 |
| D-14 | 2026-10-24 | Backend em Clean Architecture enxuta (domain / application / infrastructure / api), com teste que protege a regra de dependência | Separar regra clínica de detalhe técnico; trocar SWALIS stub pelo real sem mexer no resto | Rotas com regra de negócio direto no banco | backend |
| D-15 | 2026-10-24 | Banco: PostgreSQL 16 (Docker) com SQLModel/SQLAlchemy 2, no lugar do SQLite | Banco de verdade para o pitch; concorrência (API + CLI) sem travar arquivo; upsert nativo para a carga idempotente | SQLite (simples, mas limitado para a demo); DuckDB (analítico, escrita de um processo só) | US-01 |
| D-16 | 2026-10-24 | Sem migrations (Alembic): tabelas criadas com `create_all`; mudança de schema = `docker compose down -v` e recarga | Hackathon; dados são reproduzíveis a partir dos CSVs | Alembic | US-01 |
| D-17 | 2026-10-24 | `eventos.solicitacao_id` sem chave estrangeira | Eventos órfãos existem no dataset e nada é apagado (I-03); a US-04 os sinaliza | FK (rejeitaria os órfãos na carga) | US-01 |
| D-18 | 2026-10-24 | Piora clínica (PRE-06) = qualquer evento, durante a espera e sem ser duplicado, de PS, internação, imagem com progressão, reavaliação com piora ou paciente que relata piora. Sem janela de recência. No dataset: 199 pacientes com piora, 147 com flag "nao" corrigida | Alinha com os sinais da camada 2 e com o gatilho `relata_piora` (C-03). A US-03 pede "durante a espera", não "recente" | Só PS/internação (103 pacientes, 66 com flag "nao"); janela de 180 dias | US-03 |
| D-19 | 2026-10-24 | `piora_recalculada` = piora por evento **ou** flag original "sim": só corrige "nao" → "sim", nunca rebaixa. 36 flags "sim" ficam sem evento de apoio | A piora pode estar só no texto (SOL-2026-00637); silêncio não é estabilidade (I-08). A análise de texto (LLM) refina depois | Recalcular só por evento (rebaixaria "sim" sem evidência) | US-03 |
| D-20 | 2026-10-24 | Evento duplicado (PRE-07) = mesma solicitação, data, tipo, resultado, valor, descrição **e origem**. Fica o de menor `evento_id`; os outros recebem `duplicado_de` e não contam como piora. Nenhum é apagado. No dataset: 6 | EVT-000712/713 diferem só na origem (PS São Lucas × UPA) e podem ser dois atendimentos reais; apagar um é irreversível para o score | Ignorar a origem (7 duplicatas) | US-03 |
| D-21 | 2026-10-24 | Evento histórico (PRE-08) = `data_evento` **anterior** à `data_entrada_fila` (no dia da entrada já é espera). Evento órfão não é histórico nem duplicado. No dataset: 155. O "104 com PS/internação recente" do `fluxo-sistema.md` §12 inclui 1 paciente que só tem PS histórico; o número correto é 103 (66 com flag "nao") | A data de entrada é o corte da espera; sem solicitação não há corte | Contar o dia da entrada como histórico | US-03 |
| D-22 | 2026-10-24 | O pré-processamento (`Preprocessar`) roda ao final da carga, em segunda transação, e também avulso (`python -m app.cli preprocessar`). Recalcula as colunas derivadas e refaz só o log das suas regras (`correcoes_log`), sem tocar nas colunas originais nem em outras regras | D-04: mesmo pré-processamento para carga e eventos; reprocessar não duplica o log. Se a 2ª transação falhar, a carga fica gravada e basta reprocessar | Pré-processar só em comando separado; uma única transação (exigiria mexer no `SqlCargaRepository`) | US-03 |

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
