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
| D-11 | 2026-10-24 | Stack: FastAPI + SQLite + pandas no back; React (Vite + TS) no front | Conhecimento do time; rapidez | — | todos |
| D-12 | 2026-10-24 | Sem login: seletor de persona e de usuário fixo no front | Hackathon; o log ainda registra autores distintos | Autenticação real | US-23 |
| D-13 | 2026-10-24 | API é a fronteira back × front; back sobe mocks com o contrato final primeiro | Trabalho em paralelo sem retrabalho | Front esperar o back | US-01..US-23 |
| D-14 | 2026-10-24 | Backend em Clean Architecture enxuta (domain / application / infrastructure / api), com teste que protege a regra de dependência | Separar regra clínica de detalhe técnico; trocar SWALIS stub pelo real sem mexer no resto | Rotas com regra de negócio direto no banco | backend |
| D-15 | 2026-10-24 | ~~Camada 2 = complemento exato de "sem urgência" do verificador~~ (revista por D-20) | Mais seguro em relação à regra oficial | Camada 2 só com sinais clínicos | US-08 |
| D-16 | 2026-10-24 | Eventos de piora só contam durante a espera e não duplicados | Coerente com PRE-07/08 | Contar qualquer evento | US-08 |
| D-17 | 2026-10-24 | Câncer escondido (biópsia positiva, CID não C) vai para a camada 2 com alerta "revisar CID"; biópsia positiva conta em qualquer data | Sem a exceção, D-16 apagaria esses casos; camada 1 continua só pelo CID (Q-08 aberta) | Camada 1 pela biópsia | US-08 |
| D-18 | 2026-10-24 | Desempate na camada: score desc, entrada mais antiga, solicitacao_id | Ordem determinística; 80+ aguarda Q-10 | Desempate por idade | US-08 |
| D-19 | 2026-10-24 | CSV provisório gerado direto do dataset (sem banco) com SWALIS stub: `python -m app.cli gerar-fila-csv` | Garantir a entrega das 14h sem depender da US-01 | Esperar a US-01 | US-08/09/10 |
| D-20 | 2026-10-24 | **Revisa D-15.** Camada 2 = só sinais clínicos (CID de complicação, evento de piora na espera, biópsia positiva, alarme no texto). Dor > 3 e limitação moderada/grave viram "sintomas": aparecem na justificativa e ficam para o SWALIS (classe), sem definir camada | Com D-15, 320 dos 526 da camada 2 (61%) estavam lá só por sintoma e competiam com quem piorou; dor é autorrelatada e já é critério da classe SWALIS. A regra de ouro não muda (camada 1). Resultado: camada 2 de 526 → 206; PS/internação recente na 1ª metade de 50% → 100% | Manter D-15; 4 camadas (onco / clínico / sintomático / demais) | US-08 |

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
