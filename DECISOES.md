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
