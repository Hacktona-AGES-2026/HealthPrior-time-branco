# User stories — HealthPrior (Time Branco)

> **Status:** v1 · 24/10/2026
> **Base:** `docs/fluxo-sistema.md` (componentes `C-xx`, invariantes `I-xx`, decisões `D-xx`).
> **Fora deste documento:** as histórias do **SWALIS** (cálculo de classe/score), que serão definidas à parte. Aqui elas apenas **consomem o contrato** do SWALIS (`docs/fluxo-sistema.md` C-07). Enquanto ele não existir, use um **SWALIS stub** (ex.: classe por prioridade normalizada, score = dias em fila).

---

## 0. Como usar

- Cada história tem ID `US-xx`. Use em branches, commits e prompts: `feat(US-08): trava por camadas`, `/tarefa US-08`.
- **Prioridade (hackathon):**
  - **P0** — obrigatório até **14h** (entrega do `fila_priorizada.csv`).
  - **P1** — obrigatório até **19h** (demo do pitch).
  - **P2** — se sobrar tempo.
- Cada história indica o que é **Back** (FastAPI), **Front** (React) e o **endpoint** que conecta os dois.
- Critérios de aceite (**CA**) são o "pronto". Se um CA cita um ID de paciente, ele é um caso de teste real do dataset.

## 1. Stack e fronteira back/front

- **Back:** Python + FastAPI + PostgreSQL 16 (Docker, via SQLAlchemy 2) + pandas no pipeline (D-15).
- **Front:** React (Vite + TypeScript).
- **Regra:** o **back é dono de toda regra de negócio** (pré-processamento, score, trava, verificador, pendências, log, aprendizado). O **front só exibe e coleta decisões**.
  - Única exceção: validação de UX na edição do regulador (bloquear rebaixamento de oncológico na hora). **O back valida de novo** e tem a palavra final.
- **Sem login.** O front tem um **seletor de persona** (Regulador, Administrativo, Comitê) e um seletor de usuário fixo (ex.: `reg-01`…`reg-04`) para que o log registre autores distintos (o ciclo de aprendizado depende de "reguladores distintos").
- Data de referência fixa: `REF = 2026-10-23`.

## 2. Mapa de épicos

| Épico | Componentes | Histórias | Lado |
|---|---|---|---|
| E1 Ingestão e pré-processamento | C-02, C-05 | US-01..US-05 | Back |
| E2 Pendências | C-06 | US-06, US-07 | Back + Front |
| E3 Trava, verificação e entrega | C-11, C-12 | US-08..US-11 | Back |
| E4 Regulador | C-08, C-09, C-10 | US-12..US-14 | Back + Front |
| E5 Eventos e atualização diária | C-03, C-04, C-13 | US-15..US-17 | Back + Front |
| E6 Ciclo de aprendizado | C-14 | US-18, US-19 | Back + Front |
| E7 Visualização e navegação | — | US-20..US-23 | Back + Front |

---

## 3. Histórias

### E1 · Ingestão e pré-processamento (C-02, C-05)

#### US-01 · Carga inicial — **P0** · Back
Como **equipe**, quero carregar as 941 solicitações e ~1.500 eventos do dataset, para ter a fila inicial no sistema.
- **CA**
  - Lê `data/fila_cirurgica.csv`, `data/eventos_clinicos.csv`, `data/procedimentos.csv` e grava no PostgreSQL.
  - Valores originais preservados (colunas originais intactas; normalizados em colunas novas).
  - Idempotente: rodar duas vezes não duplica registros.
  - Carga inicial **não** passa pelo regulador; classe fica `classe_status = sugerida_nao_confirmada` (D-01).
- **Back:** comando CLI (`python -m app.cli carga`) e/ou `POST /admin/carga`.
- **Front:** —
- **Depende de:** —

#### US-02 · Normalização automática — **P0** · Back
Como **sistema**, quero padronizar CID, nome, município e prioridade, para comparar registros de forma confiável.
- **CA**
  - `cid_norm` maiúsculo sem ponto (`K42.9` e `K429` → `K429`). (PRE-01)
  - Nome normalizado para comparação (PRE-02); município mapeado para nome oficial (PRE-03); prioridade em `alta`/`media`/`baixa`/vazio (PRE-04).
  - Toda correção gravada em `correcoes_log` (campo, original, novo, regra).
  - Teste: PAC-00087 ("Jurema Quadros Weber" / "JUREMA QUADROS WEBER") normaliza para o mesmo nome; "PORTO ALEGRE" e "porto alegre" → "Porto Alegre".
- **Back:** módulo `preprocessing` com funções puras e testáveis.
- **Depende de:** US-01

#### US-03 · Flags recalculadas e eventos limpos — **P0** · Back
Como **sistema**, quero recalcular as flags pelo CID e pelos eventos, para não depender das flags manuais erradas.
- **CA**
  - `oncologico = cid_norm começa com "C"`; flag original guardada (PRE-05).
  - Piora recalculada a partir de eventos durante a espera (PRE-06).
  - Eventos duplicados marcados com `duplicado_de` (PRE-07).
  - Eventos com data anterior à entrada na fila marcados `historico = true` e **não contam como piora** (PRE-08).
  - Teste: SOL-2025-00149 (C61, flag "nao") vira oncológico; SOL-2026-00583 (K40.9, flag "sim") deixa de ser; EVT-000050/EVT-000051 → um marcado duplicado; SOL-2023-00017 tem 2 PS em histórico.
- **Depende de:** US-02

#### US-04 · Inconsistências bloqueantes — **P0** · Back
Como **sistema**, quero detectar duplicatas, desistências, cirurgias feitas fora e eventos órfãos, para não priorizar quem não está mais esperando.
- **CA**
  - Solicitação vai para `status_fila = suspensa` com `motivo_status` = regra (PRE-20..PRE-25) e gera pendência bloqueante.
  - Duplicata (mesmo `paciente_id` + `procedimento_id`): suspende a mais recente; mantém a **data de entrada mais antiga** (D-10).
  - Evento órfão não é aplicado e gera pendência.
  - **Oncológico nunca é suspenso sem confirmação humana** (I-02): fica ativo com pendência.
  - Nada é apagado (I-03).
  - Teste: PAC-00151 (SOL-2025-00290 / SOL-2025-00348), SOL-2024-00076 (desistiu), SOL-2023-00054 (outro serviço), SOL-2025-00453 (convênio), EVT-000287 (órfão), SOL-2026-00305 (fontes contraditórias).
- **Depende de:** US-03

#### US-05 · Inconsistências não bloqueantes — **P1** · Back (+ Front via US-20)
Como **sistema**, quero sinalizar contato perdido, CID suspeito, cadastro desatualizado e justificativa vazia, para que alguém corrija sem tirar o paciente da fila.
- **CA**
  - Paciente segue `ativa` com `alertas[]` e pendência não bloqueante (PRE-10..PRE-15).
  - Teste: SOL-2025-00053 (número não existe), SOL-2026-00059 (contato via ACS), SOL-2026-00757 (biópsia positiva com D37.4), SOL-2026-00444 (diabetes fora do cadastro), SOL-2026-00932 ("Solicito cirurgia.").
- **Front:** ícone de alerta na tabela da fila (US-20) e lista no detalhe (US-21).
- **Depende de:** US-03

---

### E2 · Pendências (C-06)

#### US-06 · Lista de pendências — **P1** · Back + Front
Como **equipe administrativa**, quero ver as pendências abertas com motivo, evidência e ação sugerida, para saber o que resolver.
- **CA**
  - Filtros: `bloqueante`, `regra`, `status`.
  - Cada item mostra evidência de origem (trecho ou evento); em fontes contraditórias, as duas evidências lado a lado.
- **Back:** `GET /pendencias`
- **Front:** tela "Pendências" (persona Administrativo).
- **Depende de:** US-04, US-05

#### US-07 · Resolver pendência — **P1** · Back + Front
Como **equipe administrativa**, quero resolver uma pendência (confirmar saída, fundir duplicata, reativar ou descartar), para manter a fila limpa.
- **CA**
  - Resolver reprocessa a solicitação (volta ao fluxo) ou a remove **com motivo** (`status_fila = removida`).
  - Grava `resolvido_por`, `resolvido_em`, `resolucao`. Nada é apagado.
  - Fila é recalculada após a resolução (trava + verificador).
- **Back:** `POST /pendencias/{id}/resolver`
- **Front:** botões de ação no item + campo de observação.
- **Depende de:** US-06, US-08

---

### E3 · Trava, verificação e entrega (C-11, C-12)

#### US-08 · Trava da regra de ouro — **P0** · Back
> **Status: ✅ implementada** (branch `feat/US-08-trava-regra-de-ouro`). Detalhes e decisões D-22..D-27: `docs/implementacao/US-08-trava-regra-de-ouro.md`.

Como **sistema**, quero ordenar a fila por camadas, para que nenhum oncológico fique abaixo de paciente sem urgência (I-01).
- **CA**
  - Camada 1: oncológicos (`cid_norm` C*). Camada 2: urgentes não oncológicos (biópsia positiva, PS/internação durante a espera, progressão, reavaliação com piora, CID de complicação, sinais de alarme). Camada 3: demais.
  - Dentro da camada: `score_efetivo` (= `score_medico` se houver, senão `score_sistema`), desc.
  - Funciona com o SWALIS stub.
  - Camada 2 = só sinais clínicos; dor > 3 e limitação moderada/grave são sintomas (justificativa + SWALIS), não camada (D-27). A regra de ouro é garantida pela camada 1.
- **Back:** módulo `ranking` (função pura `ordenar(solicitacoes) -> lista`).
- **Depende de:** US-03 (+ SWALIS ou stub)

#### US-09 · Gerar `fila_priorizada.csv` — **P0** · Back
> **Status: ✅ implementada** (branch `feat/US-09-gerar-fila-banco`): `python -m app.cli gerar-fila` e `GET /fila/export` a partir do banco. Registro: `docs/implementacao/US-09-gerar-fila-banco.md` (D-34..D-36). O `gerar-fila-csv` (sem banco, D-26) continua como alternativa.

Como **equipe**, quero gerar o CSV de entrega com justificativa legível por paciente.
- **CA**
  - Colunas obrigatórias: `solicitacao_id`, `posicao`, `justificativa`. Recomendadas: `camada`, `classe`, `pct_prazo_consumido`, `dias_em_fila`, `editado_manualmente`, `versao_regras`.
  - Justificativa explica a posição. Ex.: "Camada 1 (oncológico C18.7). Classe A2: biópsia positiva em 30/01/2023. 1.318 dias em fila."
  - Suspensos/removidos ficam fora.
  - Teste: SOL-2023-00010 nas primeiras posições.
- **Back:** CLI `python -m app.cli exportar` e `GET /fila/export`.
- **Front:** botão "Baixar CSV" (P2).
- **Depende de:** US-08

#### US-10 · Verificador como portão — **P0** · Back
> **Status: ✅ implementada** (branch `feat/US-10-verificador-portao`): `PublicarFila` (candidato → verificador → publica no banco e no arquivo), `POST /admin/publicar-fila`, `GET /fila/export` só da fila publicada e CI no GitHub Actions. Registro: `docs/implementacao/US-10-verificador-portao.md` (D-37..D-43). Banner no front (P2) pendente.

Como **equipe**, quero que a fila só seja publicada se passar no verificador oficial, para nunca entregar uma fila desclassificada (I-07).
- **CA**
  - Após gerar a fila, roda `src/verificar_fila_priorizada.py`. Passou → marca como publicada. Falhou → mantém a fila anterior publicada e registra alerta.
  - GitHub Actions roda o verificador sobre a fila gerada a cada push.
- **Front:** banner "fila não publicada" quando `publicada = false` (P2).
- **Depende de:** US-09

#### US-11 · Exclusões no `DECISOES.md` — **P0** · Back
Como **equipe**, quero listar no `DECISOES.md` quem ficou fora da fila e por quê, como o desafio pede.
- **CA**
  - Comando gera a tabela "Solicitações fora da fila" agrupada por motivo (regra PRE-xx), com contagem e IDs.
  - Bate com o aviso de cobertura do verificador.
- **Back:** CLI `python -m app.cli decisoes`.
- **Depende de:** US-04

---

### E4 · Regulador (C-08, C-09, C-10)

#### US-12 · Inbox do regulador — **P1** · Back + Front
> **Status: ✅ back implementado** (branch `feat/US-12-inbox`): `GET /inbox` calculado na leitura; 296 itens no dataset. Registro: `docs/implementacao/US-12-inbox.md` (D-64..D-67). Tela do front pendente.

Como **regulador**, quero ver só os pacientes com classe nova ou alterada, com motivo e evidência, para decidir rápido sem revisar a fila inteira.
- **CA**
  - Item entra no inbox quando `classe_sugerida != classe_atual` (ou classe nova de entrada nova). Eventos sem mudança de classe **não** entram (D-02).
  - Card: classe atual → sugerida, motivos, evidência citada (evento/trecho), dias em fila, camada.
  - Se o paciente tem override anterior: aviso "editado por X em DD/MM".
- **Back:** `GET /inbox`
- **Front:** tela "Inbox" (persona Regulador), cards ordenados por gravidade da classe sugerida.
- **Depende de:** US-08 (+ SWALIS ou stub)

#### US-13 · Aprovar proposta — **P1** · Back + Front
Como **regulador**, quero aprovar a classe sugerida com um clique.
- **CA**
  - `classe_status = confirmada`; registro no log de decisões; fila recalculada (trava + verificador).
  - Resposta traz a nova posição do paciente.
- **Back:** `POST /decisoes` com `acao = "aprovar"`.
- **Front:** botão "Aprovar" no card; feedback com a nova posição.
- **Depende de:** US-12

#### US-14 · Editar classe ou score com justificativa — **P1** · Back + Front
Como **regulador**, quero editar a classe ou o score (ou manter a classe atual) com justificativa, para corrigir o que o sistema não captou.
- **CA**
  - `motivo_codificado` + `justificativa` obrigatórios para `editar` e `manter`.
  - Grava `classe_medico`/`score_medico`, `editado_manualmente = true`, `editado_por`, `editado_em`. Score editado continua envelhecendo.
  - **Back retorna 422 `ONCOLOGICO_REBAIXADO`** se a edição colocaria um oncológico abaixo de paciente sem urgência (I-01). **Front bloqueia antes** com a mensagem "Oncológico não pode ficar abaixo de paciente sem urgência".
  - Edita classe/score, **nunca posição** (D-03).
- **Back:** `POST /decisoes` com `acao = "editar" | "manter"`.
- **Front:** modal de edição (classe, score, motivo em lista, texto livre).
- **Depende de:** US-12

---

### E5 · Eventos e atualização diária (C-03, C-04, C-13)

#### US-15 · Registrar evento novo — **P1** · Back + Front
Como **sistema** (e, na demo, como **apresentador**), quero inserir um evento e ver o paciente ser reavaliado.
- **CA**
  - Evento passa por pré-processamento → SWALIS → se a classe mudou, vai ao inbox; senão, só é registrado.
  - Resposta informa o desfecho: `registrado`, `enviado_inbox` ou `pendencia`.
  - **Cena da demo:** PS para SOL-2023-00060 (vesícula) → aparece no inbox → regulador aprova → paciente sobe.
- **Back:** `POST /eventos`
- **Front:** formulário "Novo evento" (tipo, resultado, data, descrição, origem).
- **Depende de:** US-03, US-12

#### US-16 · Atualização diária — **P2** · Back + Front
Como **sistema**, quero recalcular o % do prazo de todos uma vez por dia, para a fila envelhecer sozinha.
- **CA**
  - Recalcula score efetivo (inclusive overrides), aplica eventos registrados, roda trava + verificador.
  - Disparo manual para a demo (sem cron real).
- **Back:** `POST /admin/atualizacao-diaria` (`?data=AAAA-MM-DD` opcional; resposta = a do `publicar-fila` + `data_referencia`)
- **Front:** botão "Rodar atualização diária".
- **Depende de:** US-10

> **Status: back implementado** (branch `feat/US-16-atualizacao-diaria`, D-76): relógio simulado, data em `fila_publicada.data_referencia`, fila e detalhe usam a mesma. Recontato (passo 3 do C-13) é a US-17; botão no front pendente.

#### US-17 · Recontato de quem está sem eventos — **P2** · Back
Como **equipe administrativa**, quero ser avisada de quem está sem eventos há N dias, para não confundir silêncio com estabilidade (I-08).
- **CA**
  - N configurável; gera pendência "recontato" (aparece em US-06).
  - Não altera prioridade.
- **Depende de:** US-06, US-16

---

### E6 · Ciclo de aprendizado (C-14)

#### US-18 · Agrupar justificativas em propostas — **P2** · Back
Como **sistema**, quero agrupar edições parecidas dos reguladores em propostas de regra.
- **CA**
  - Agrupa por `procedimento + motivo_codificado + classe_de → classe_para`.
  - Filtros configuráveis (padrão provisório): ≥5 casos, ≥3 reguladores distintos, últimos 90 dias, ≥80% na mesma direção.
  - Motivos `outro` agrupados por LLM (com cache).
  - Propostas que rebaixariam oncológico são descartadas (I-01).
  - Seed: ~30 decisões sintéticas formando 2–3 padrões para a demo.
- **Back:** `POST /aprendizado/gerar-propostas`
- **Depende de:** US-14

#### US-19 · Comitê aprova a regra — **P2** · Back + Front
Como **comitê clínico**, quero ver a proposta, os casos de origem e o impacto simulado, para aprovar ou rejeitar.
- **CA**
  - Impacto simulado (shadow run): quantos mudariam de classe, quantos oncológicos afetados (deve ser 0 de rebaixamento).
  - Aprovar cria nova `versao_regras`; pacientes afetados entram no inbox (US-12).
  - Rejeitar registra motivo.
- **Back:** `GET /propostas`, `POST /propostas/{id}/decidir`
- **Front:** tela "Propostas" (persona Comitê).
- **Depende de:** US-18

---

### E7 · Visualização e navegação

#### US-20 · Ver a fila priorizada — **P1** · Back + Front
> **Status: ✅ back implementado** (branch `feat/US-20-fila-api`): `GET /fila` real a partir da fila publicada. Registro: `docs/implementacao/US-20-fila-api.md` (D-56..D-58). Tela do front pendente.

Como **regulador ou gestor**, quero ver a fila ordenada com camada, classe, % do prazo, dias de espera, flag de edição manual e alertas.
- **CA**
  - Paginação; filtros por camada, procedimento, especialidade; busca por `solicitacao_id`.
  - Destaque visual de camada e de `editado_manualmente`.
- **Back:** `GET /fila`
- **Front:** tela "Fila" (padrão ao abrir o app).
- **Depende de:** US-08

#### US-21 · "Por que este paciente está aqui?" — **P1** · Back + Front
> **Status: ✅ back implementado** (branch `feat/US-21-detalhe-paciente`): `GET /solicitacoes/{id}` com explicação, score, motivos, eventos, pendências e correções. Registro: `docs/implementacao/US-21-detalhe-paciente.md` (D-68..D-70). Tela do front pendente.

Como **regulador**, quero abrir um paciente e ver a explicação da posição dele.
- **CA**
  - Mostra: camada e por quê, classe (sistema × médico), % do prazo, motivos com evidência, linha do tempo de eventos (histórico separado), decisões, pendências e correções automáticas.
  - A explicação é **montada pelo back** (`explicacao` em texto + estrutura).
- **Back:** `GET /solicitacoes/{id}`
- **Front:** tela/drawer de detalhe.
- **Depende de:** US-08

#### US-22 · Antes × depois — **P1** · Back + Front
> **Status: ✅ back implementado** (branch `feat/US-22-antes-depois`): `GET /metricas/comparacao`. "Antes": 177 violações, mediana dos oncológicos 287. Registro: `docs/implementacao/US-22-antes-depois.md` (D-59..D-62). Tela do front pendente.

Como **apresentador**, quero comparar a fila atual (prioridade manual + data) com a proposta.
- **CA**
  - Métricas: violações da regra de ouro (hoje 177 → 0), posição mediana dos oncológicos, % PS/internação recente na 1ª metade, % sem urgência no último terço.
  - Destaques: SOL-2023-00010 (posição 606 hoje → topo), SOL-2025-00048.
- **Back:** `GET /metricas/comparacao`
- **Front:** tela "Antes × depois".
- **Depende de:** US-09

#### US-23 · Navegação e seletor de persona — **P1** · Front
> **Status: cortada** (D-100). Sem personas e sem seletor de usuário; menu único. Autor fixo por papel em `web/src/lib/usuario.ts` (`reg-01` decisões, `adm-01` pendências).

Como **usuário**, quero alternar entre as visões de Regulador, Administrativo e Comitê, sem login.
- **CA**
  - Layout com menu: Fila, Inbox, Pendências, Propostas, Antes × depois, Novo evento.
  - Seletor de persona muda o menu visível; seletor de usuário (`reg-01`…`reg-04`, `adm-01`, `com-01`) define o autor enviado nas decisões.
  - Persona/usuário guardados em `localStorage`.
- **Front:** layout + contexto de persona.
- **Depende de:** —

---

## 4. Divisão back × front

| US | Back | Front | Endpoint |
|---|---|---|---|
| US-01 | Carga dos CSVs no PostgreSQL | — | `POST /admin/carga` / CLI |
| US-02 | PRE-01..04 + log | — | interno |
| US-03 | PRE-05..08 | — | interno |
| US-04 | PRE-20..25, suspensão | — | interno |
| US-05 | PRE-10..15, alertas | Ícone de alerta | via `GET /fila` |
| US-06 | Consulta filtrada | Tela Pendências | `GET /pendencias` |
| US-07 | Resolução + reprocesso | Ações no item | `POST /pendencias/{id}/resolver` |
| US-08 | Ordenação por camadas | — | interno |
| US-09 | CSV + justificativa | Botão baixar (P2) | `GET /fila/export` / CLI |
| US-10 | Verificador + CI | Banner (P2) | interno |
| US-11 | Lista de exclusões | — | CLI |
| US-12 | Itens com mudança de classe | Tela Inbox | `GET /inbox` |
| US-13 | Confirma + log + recálculo | Botão aprovar | `POST /decisoes` |
| US-14 | Valida + override + log | Modal de edição + bloqueio UX | `POST /decisoes` |
| US-15 | Pipeline do evento | Formulário de evento | `POST /eventos` |
| US-16 | Recálculo diário | Botão | `POST /admin/atualizacao-diaria` |
| US-17 | Pendências de recontato | (via Pendências) | — |
| US-18 | Agrupamento + LLM | — | `POST /aprendizado/gerar-propostas` |
| US-19 | Shadow run + versão | Tela Propostas | `GET /propostas`, `POST /propostas/{id}/decidir` |
| US-20 | Lista paginada | Tabela da fila | `GET /fila` |
| US-21 | Explicação montada | Detalhe do paciente | `GET /solicitacoes/{id}` |
| US-22 | Métricas antes × depois | Tela comparação | `GET /metricas/comparacao` |
| US-23 | — | ~~Layout + persona~~ cortada (D-100) | — |

**Observação:** todo o P0 é back. O front começa em paralelo, contra mocks (seção 6).

---

## 5. Contrato da API (endpoints que o front consome)

Convenções: JSON em `snake_case`; datas `AAAA-MM-DD`; IDs como no dataset; erros no formato
`{"erro": "<CODIGO>", "mensagem": "<texto para o usuário>"}`.

Enums:
- `camada`: `1 | 2 | 3`
- `classe`: `"A1" | "A2" | "B" | "C" | "D"`
- `classe_status`: `"sugerida_nao_confirmada" | "confirmada"`
- `status_fila`: `"ativa" | "suspensa" | "removida"`
- `motivo_codificado`: `"ps_recorrente" | "internacao_relacionada" | "progressao_imagem" | "piora_funcional" | "dor_intensa" | "biopsia_positiva" | "sinal_alarme_texto" | "sugestao_exagerada" | "dado_desatualizado" | "outro"`

### 5.1 `GET /fila`
Query: `camada?`, `procedimento_id?`, `especialidade?`, `busca?`, `page=1`, `page_size=50`.
```json
{
  "versao_regras": "v1",
  "gerada_em": "2026-10-24T10:00:00",
  "publicada": true,
  "total": 900,
  "itens": [
    {
      "posicao": 1,
      "solicitacao_id": "SOL-2023-00010",
      "camada": 1,
      "classe": "A2",
      "classe_status": "sugerida_nao_confirmada",
      "pct_prazo_consumido": 6276.2,
      "dias_em_fila": 1318,
      "procedimento": "Colectomia",
      "especialidade": "Cirurgia Oncologica",
      "cid": "C18.7",
      "oncologico": true,
      "editado_manualmente": false,
      "alertas": ["contato_perdido"],
      "resumo_justificativa": "Camada 1 (oncológico C18.7). Biópsia positiva em 30/01/2023."
    }
  ]
}
```

### 5.2 `GET /solicitacoes/{solicitacao_id}`
```json
{
  "solicitacao_id": "SOL-2023-00010",
  "paciente_id": "PAC-00467",
  "nome_paciente": "…",
  "idade": 62,
  "sexo": "M",
  "municipio": "Pelotas",
  "procedimento": "Colectomia",
  "cid": "C18.7",
  "cid_descricao": "…",
  "status_fila": "ativa",
  "posicao": 1,
  "camada": 1,
  "camada_motivo": "Oncológico pelo CID (C18.7)",
  "score": {
    "classe_sistema": "A2",
    "score_sistema": 6276.2,
    "classe_medico": null,
    "score_medico": null,
    "score_efetivo": 6276.2,
    "prazo_dias": 21,
    "pct_prazo_consumido": 6276.2,
    "classe_status": "sugerida_nao_confirmada",
    "versao_regras": "v1",
    "motivos": [
      { "sinal": "biopsia_positiva", "evidencia": "Adenocarcinoma…", "fonte": "evento", "ref": "EVT-000013", "data": "2023-01-30" }
    ]
  },
  "explicacao": "Está na posição 1 porque é oncológico (camada 1) e já consumiu …",
  "eventos": [
    { "evento_id": "EVT-000013", "data_evento": "2023-01-30", "tipo_evento": "biopsia", "resultado": "positivo", "descricao": "…", "historico": true, "duplicado": false }
  ],
  "decisoes": [
    { "decisao_id": "DEC-0001", "data": "2026-10-24", "regulador_id": "reg-01", "acao": "aprovar", "classe_decidida": "A2", "motivo_codificado": null, "justificativa": null }
  ],
  "pendencias": [ { "pendencia_id": "PEN-0001", "regra": "PRE-10", "bloqueante": false, "status": "aberta" } ],
  "alertas": ["contato_perdido"],
  "correcoes": [ { "campo": "flag_oncologico", "original": "nao", "novo": "sim", "regra": "PRE-05" } ]
}
```
*(Os valores numéricos acima são ilustrativos; o score real vem do SWALIS.)*

### 5.3 `GET /inbox`
Query: `regulador_id?`.
```json
{
  "total": 12,
  "itens": [
    {
      "solicitacao_id": "SOL-2023-00060",
      "procedimento": "Colecistectomia videolaparoscopica",
      "camada": 2,
      "dias_em_fila": 1109,
      "classe_atual": "C",
      "classe_sugerida": "B",
      "motivos": [
        { "sinal": "ps_recorrente", "evidencia": "2 idas ao PS em 3 meses", "fonte": "evento", "ref": "EVT-…", "data": "2026-10-20" }
      ],
      "evento_gatilho": "EVT-…",
      "editado_anteriormente": { "por": "reg-02", "em": "2026-10-12" },
      "criado_em": "2026-10-24T10:05:00"
    }
  ]
}
```

### 5.4 `POST /decisoes`
Request:
```json
{
  "solicitacao_id": "SOL-2023-00060",
  "regulador_id": "reg-01",
  "acao": "aprovar",
  "classe": null,
  "score": null,
  "motivo_codificado": null,
  "justificativa": null
}
```
- `acao = "aprovar"`: aceita a classe sugerida.
- `acao = "editar"`: exige `classe` **ou** `score`, mais `motivo_codificado` e `justificativa`.
- `acao = "manter"`: recusa a sugestão; exige `motivo_codificado` e `justificativa`.

Resposta `200`:
```json
{ "decisao_id": "DEC-0002", "posicao_anterior": 536, "posicao_nova": 140, "fila_publicada": true }
```
Erros:
- `422 {"erro": "ONCOLOGICO_REBAIXADO", "mensagem": "Oncológico não pode ficar abaixo de paciente sem urgência."}`
- `422 {"erro": "JUSTIFICATIVA_OBRIGATORIA", "mensagem": "…"}`
- `404 {"erro": "SOLICITACAO_NAO_ENCONTRADA", "mensagem": "…"}`

### 5.5 `POST /eventos`
Request:
```json
{
  "solicitacao_id": "SOL-2023-00060",
  "data_evento": "2026-10-23",
  "tipo_evento": "pronto_socorro",
  "resultado": "observacao",
  "valor_numerico": null,
  "descricao": "Dor em hipocôndrio direito, febre. Colecistite aguda.",
  "origem": "PS Hospital Sao Lucas"
}
```
Resposta `201`:
```json
{ "evento_id": "EVT-001506", "desfecho": "enviado_inbox", "classe_antes": "C", "classe_depois": "B", "pendencia_id": null }
```
`desfecho`: `"registrado" | "enviado_inbox" | "pendencia"`.
Erros: `404 SOLICITACAO_NAO_ENCONTRADA` (vira pendência de evento órfão quando vier de integração), `422 EVENTO_INVALIDO`.

### 5.6 `GET /pendencias` e `POST /pendencias/{id}/resolver`
`GET` query: `bloqueante?`, `regra?`, `status=aberta`.
```json
{
  "total": 64,
  "itens": [
    {
      "pendencia_id": "PEN-0007",
      "solicitacao_id": "SOL-2026-00305",
      "regra": "PRE-25",
      "titulo": "Fontes contraditórias",
      "bloqueante": true,
      "evidencias": [
        { "fonte": "evento", "ref": "EVT-000566", "texto": "Pct informa que nao deseja mais realizar a cirurgia." },
        { "fonte": "observacoes", "ref": null, "texto": "Familiar informa que paciente operou pelo convenio." }
      ],
      "acao_sugerida": "Ligar para confirmar o motivo da saída",
      "status": "aberta",
      "aberta_em": "2026-10-24"
    }
  ]
}
```
`POST /pendencias/{id}/resolver` request:
```json
{ "resolucao": "confirmar_saida", "usuario_id": "adm-01", "observacao": "Confirmado: operou pelo convênio.", "fundir_com": null }
```
`resolucao`: `"confirmar_saida" | "fundir" | "reativar" | "descartar"`. Resposta `200`: `{ "status_fila": "removida", "fila_publicada": true }`.

- `status_fila` é o da solicitação da pendência depois de resolver, ou `null` quando não há solicitação (PRE-24, evento órfão).
- `fila_publicada = false`: a resolução valeu, mas o verificador reprovou (ou a publicação falhou) e a fila anterior segue publicada (I-07).
- `observacao` é obrigatória em `confirmar_saida`. Cada regra aceita só algumas resoluções (D-87); `fundir_com` é a solicitação que permanece (padrão: a mais antiga das duas duplicadas).
- Erros: `404 PENDENCIA_NAO_ENCONTRADA`, `409 PENDENCIA_JA_RESOLVIDA`, `422 RESOLUCAO_INVALIDA`, `422 OBSERVACAO_OBRIGATORIA`.
- Depois de resolvida, a pendência traz `resolvido_por`, `resolvido_em`, `resolucao` e `observacao` em `GET /pendencias?status=resolvida|descartada` (`null` enquanto aberta).

### Endpoints secundários (contrato livre, definir ao implementar)
`GET /fila/export`, `GET /metricas/comparacao`, `POST /admin/carga`, `POST /admin/atualizacao-diaria`, `POST /aprendizado/gerar-propostas`, `GET /propostas`, `POST /propostas/{id}/decidir`.

---

## 6. Trabalho em paralelo (mocks)

1. **Primeiro passo do back:** criar os schemas Pydantic da seção 5 e subir os 6 endpoints retornando **dados fixos** com esse formato (usar pacientes reais do dataset nos mocks).
2. O FastAPI publica o OpenAPI em `/openapi.json` e a documentação em `/docs`.
3. **Front:** gerar tipos TypeScript a partir do OpenAPI (ex.: `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.ts`) e desenvolver contra os mocks. Agentes de IA do front **não inventam campos**: usam os tipos gerados.
4. Quando o back troca mock por implementação real, o front não muda.
5. Mudou o contrato? Atualize esta seção **e** os schemas no mesmo PR.

---

## 7. Caminho crítico

| Até | Histórias | Resultado |
|---|---|---|
| **14h** | US-01, US-02, US-03, US-04, US-08, US-09, US-10, US-11 | `fila_priorizada.csv` válido + `DECISOES.md` |
| **19h** | US-12..US-15, US-20..US-22 (US-05..US-07 se der; US-23 cortada, D-100) | Demo: fila, detalhe, inbox, evento ao vivo, antes × depois |
| Bônus | US-16..US-19 | Atualização diária, recontato, ciclo de aprendizado |

Em paralelo desde o início: back sobe mocks da seção 5; front faz as telas contra os mocks (US-23 cortada, D-100).
