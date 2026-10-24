# HealthPrior — Time Branco

Priorização da fila de cirurgias eletivas do SUS (Desafio 1 · 9ª Hackatona de Engenharia de Software 2026 ·
Fin-X · PUCRS · Hospital São Lucas). **Dados 100% sintéticos**; data de referência **23/10/2026**.

A fila atual é ordenada por prioridade manual (ruidosa e quase nunca revisada) e data de entrada. O sistema
recalcula a ordem pela urgência clínica e pelo tempo de espera, **explica cada posição** e deixa a decisão
clínica com o regulador.

## O que o sistema entrega
- **Fila priorizada** (941 solicitações no dataset; 900 publicadas, as demais são suspensas ou duplicatas), com a
  justificativa de cada posição.
- **Regra de ouro** garantida por código: nenhum paciente oncológico (CID iniciado por `C`) fica abaixo de um
  paciente sem urgência clínica.
- **Inbox do regulador:** aprova, edita ou mantém a classe sugerida, sempre com decisão humana registrada.
- **Pendências administrativas:** problemas de dado são sinalizados, nunca apagados.
- **Eventos novos, atualização diária e recontato** de quem está sem notícias.
- **Ciclo de aprendizado:** justificativas dos reguladores viram propostas de regra que o comitê aprova ou rejeita.
- **Comparação antes × depois** (`GET /metricas/comparacao`), importação de CSV, notificações de demonstração e deploy em nuvem.

## Páginas
| Página | Conteúdo |
|---|---|
| [Fluxo do sistema](Fluxo-do-sistema.md) | Personas, entradas, portões de segurança, componentes |
| [Regras de priorização](Regras-de-priorizacao.md) | Camadas, SWALIS, score, regra de ouro e invariantes |
| [Arquitetura](Arquitetura.md) | Back, front, camadas e regra de dependência |
| [API](API.md) | Endpoints e convenções |
| [Como rodar](Como-rodar.md) | Ambiente local, comandos, testes |
| [Verificação e testes](Verificacao-e-testes.md) | Verificador oficial, CI, o que cada portão garante |
| [Importação de CSV](Importacao-de-CSV.md) | Pacientes novos pela tela ou pela API |
| [Notificações](Notificacoes.md) | Avisos ao paciente (demonstração) |
| [Deploy](Deploy.md) | Vercel, Render e Neon |
| [Decisões](Decisoes.md) | Como ler e registrar o `DECISOES.md` |

## Documentos de referência no repositório
[`docs/fluxo-sistema.md`](../fluxo-sistema.md) · [`docs/user-stories.md`](../user-stories.md) ·
[`docs/swalis.md`](../swalis.md) · [`docs/arquitetura-backend.md`](../arquitetura-backend.md) ·
[`docs/dicionario_dados.md`](../dicionario_dados.md) · [`DECISOES.md`](../../DECISOES.md) ·
[`AGENTS.md`](../../AGENTS.md)
