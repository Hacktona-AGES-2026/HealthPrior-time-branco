# API

A documentação interativa fica em `/docs` (Swagger) e o contrato em `/openapi.json` de qualquer instância.
Contrato comentado: [`docs/user-stories.md`](../user-stories.md) §5. Os erros trazem código estável (por exemplo `409 SEM_PROPOSTA`,
`422` para oncológico rebaixado).

| Método e rota | Para quê |
|---|---|
| `GET /health` | Estado do serviço e se está usando mocks |
| `GET /fila` | Fila publicada, paginada (`page`, `page_size` até 200; filtros `camada`, `procedimento_id`, `especialidade`, `busca`) |
| `GET /fila/export` | CSV da fila publicada (`solicitacao_id`, `posicao`, `justificativa` + colunas extras) |
| `GET /solicitacoes/{id}` | Ficha: explicação, motivos com evidência, eventos, decisões, pendências, alertas |
| `GET /solicitacoes/{id}/previa` | Prévia da posição antes de decidir |
| `GET /inbox` | Casos aguardando o regulador |
| `POST /decisoes` | Aprovar, editar ou manter (com justificativa) |
| `POST /eventos` | Registrar evento novo |
| `GET /pendencias` | Lista com filtros `bloqueante`, `regra`, `status` |
| `POST /pendencias/{id}/resolver` | Confirmar saída, fundir, reativar ou descartar |
| `POST /pendencias/{id}/sugerir-cid` | LLM sugere o CID do laudo (câncer escondido); quem confirma é humano |
| `POST /aprendizado/gerar-propostas` | Agrupa justificativas em propostas de regra |
| `GET /propostas` | Propostas de regra |
| `POST /propostas/{id}/decidir` | Comitê aprova ou rejeita |
| `POST /regras/{id}/reverter` | Volta a uma versão anterior das regras |
| `GET /metricas/comparacao` | Antes × depois |
| `POST /importacao/solicitacoes`, `GET /importacao/modelo.csv` | Importação de CSV |
| `GET /notificacoes`, `POST /notificacoes/enviar` | Avisos ao paciente (demonstração) |
| `POST /admin/carga`, `/admin/atualizacao-diaria`, `/admin/publicar-fila` | Operação: carga, atualização diária e republicação |

Convenções: ids de texto (`SOL-AAAA-NNNNN`), datas ISO; não há login, o autor das decisões é fixo por papel (D-107).
