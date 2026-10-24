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
| D-18 | 2026-10-24 | `correcoes_log` registra mudanças de valor visíveis (município, prioridade, CID com minúscula/espaço). Chaves de comparação (`cid_norm` sem ponto, `nome_norm`) não geram log | 816 dos 941 CIDs têm ponto e quase todo nome difere só na caixa: ~1.700 linhas de ruído sem informação. O original fica sempre intacto na coluna de origem | Logar toda diferença entre original e `*_norm` (cumpre o CA "toda correção" ao pé da letra) | US-02 |
| D-19 | 2026-10-24 | `municipio_norm` usa o nome oficial do IBGE **com acento** (Gravataí, Osório, Viamão), via tabela fixa em `domain/preprocessing/municipios.py` com os 38 municípios do dataset; município fora da tabela só perde espaços sobrando | PRE-03 pede o nome oficial; o dataset vem sem acento | Forma canônica sem acento (só unifica a caixa) | US-02 |
| D-20 | 2026-10-24 | A normalização roda dentro da carga (mesma transação) e também avulsa (`python -m app.cli normalizar`). Recalcula as colunas `*_norm` e refaz o log de PRE-01..04, sem tocar nas outras regras | D-04: mesmo pré-processamento para carga e eventos; evita carga sem normalizar | Só comando separado | US-02 |
| D-21 | 2026-10-24 | `nome_norm` = minúsculo, sem acento, espaços colapsados; prioridade desconhecida vira vazia e é registrada no log | PRE-02 e PRE-04 não definem o formato; é só chave de comparação | Maiúsculo; rejeitar a carga com prioridade inválida | US-02 |
| D-22 | 2026-10-24 | ~~Camada 2 = complemento exato de "sem urgência" do verificador~~ (revista por D-27) | Mais seguro em relação à regra oficial | Camada 2 só com sinais clínicos | US-08 |
| D-23 | 2026-10-24 | Eventos de piora só contam durante a espera e não duplicados | Coerente com PRE-07/08 | Contar qualquer evento | US-08 |
| D-24 | 2026-10-24 | Câncer escondido (biópsia positiva, CID não C) vai para a camada 2 com alerta "revisar CID"; biópsia positiva conta em qualquer data | Sem a exceção, D-23 apagaria esses casos; camada 1 continua só pelo CID (Q-08 aberta) | Camada 1 pela biópsia | US-08 |
| D-25 | 2026-10-24 | Desempate na camada: score desc, entrada mais antiga, solicitacao_id | Ordem determinística; 80+ aguarda Q-10 | Desempate por idade | US-08 |
| D-26 | 2026-10-24 | CSV provisório gerado direto do dataset (sem banco) com SWALIS stub: `python -m app.cli gerar-fila-csv` | Garantir a entrega das 14h sem depender da US-01 | Esperar a US-01 | US-08/09/10 |
| D-27 | 2026-10-24 | **Revisa D-22.** Camada 2 = só sinais clínicos (CID de complicação, evento de piora na espera, biópsia positiva, alarme no texto). Dor > 3 e limitação moderada/grave viram "sintomas": aparecem na justificativa e ficam para o SWALIS (classe), sem definir camada | Com D-22, 320 dos 526 da camada 2 (61%) estavam lá só por sintoma e competiam com quem piorou; dor é autorrelatada e já é critério da classe SWALIS. A regra de ouro não muda (camada 1). Resultado: camada 2 de 526 → 206; PS/internação recente na 1ª metade de 50% → 100% | Manter D-22; 4 camadas (onco / clínico / sintomático / demais) | US-08 |
| D-28 | 2026-10-24 | Separar gerar (US-09, `GerarFila`) de publicar (US-10, `PublicarFila`) | Responsabilidade única; cada parte testável | Um caso de uso só com tudo | US-09/10 |
| D-29 | `LinhaFila` no domínio; `FilaRepository` usa `list[LinhaFila]` | Repositório precisa da justificativa; domínio não importa aplicação | Novo tipo duplicado na infraestrutura | US-09 |
| D-30 | `GET /fila/export` gera a fila na hora (US-09); na US-10 passa a servir só a fila publicada | Endpoint funcional já; segurança vem com a US-10 | Esperar a US-10 | US-09 |

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
