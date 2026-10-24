# HealthPrior · front-end da regulação da fila cirúrgica

Vite + React + TypeScript + Tailwind v4 + shadcn/ui.

## Como rodar

```bash
npm install && npm run dev
npm run build
```

## De onde vêm os dados

- **API (padrão):** o front lê a fila publicada do backend (`GET /fila` + `GET /inbox`) em `src/data/fila.ts` (`carregarFila`). Os campos que a API não expõe (justificativa clínica, ASA, HbA1c, pré-operatório, sinais do texto) vêm do JSON abaixo, juntados pelo id da solicitação (`src/data/adaptador.ts`).
- **CSVs (sem API):** `src/data/dados.json` é gerado por `scripts/gerar_dados.py`, que roda o pipeline do `backend/` sobre `data/*.csv` (carga, normalização, SWALIS por regras com cache do LLM e trava de camadas). O nome do paciente nunca vai para o JSON (só iniciais). Sem API o front cai nesses dados, mostra um aviso e guarda as decisões só no navegador.
- URL da API: `VITE_API_URL` (padrão `http://127.0.0.1:8000`; veja `.env.example`). Suba o back com `HP_USE_MOCKS=false`, a carga e a fila publicada.

```bash
python -m venv .venv && .venv/bin/pip install pandas pydantic fastapi sqlmodel httpx "psycopg[binary]"
.venv/bin/python web/scripts/gerar_dados.py   # a partir da raiz do repositório
```

## Ações com a API

- **Aprovar** → `POST /decisoes` (`aprovar`, só para quem está no inbox: fora dele a API responde 409 `SEM_PROPOSTA` e o botão fica desabilitado, D-94); **Editar** → `POST /decisoes` (`editar`, com classe, motivo codificado e justificativa); **Registrar evento** → `POST /eventos`. Depois de cada ação a fila é recarregada. Decisão na API não se desfaz: para mudar, edite de novo com justificativa.
- Página **Inbox**: propostas do SWALIS que aguardam um profissional. Página **Pendências** (US-06): `GET /pendencias`.
- Ficha com a API: `GET /solicitacoes/{id}` mostra explicação, motivos do SWALIS, decisões do regulador, pendências e os eventos registrados.

Os tipos da API são **gerados**: com o back no ar, `npm run gen:api` atualiza `src/api/schema.ts` (`OPENAPI_URL=... npm run gen:api` para outra URL). O gerador roda via `npx` porque exige TypeScript 5 e o projeto usa o 6 (D-85).

## Propostas (US-19)

A página **Propostas** lê `GET /propostas` (abas: para decidir, aprovadas, rejeitadas, descartadas) e decide com `POST /propostas/{id}/decidir`. Para ver propostas na demo: `python -m app.cli seed-aprendizado` e `python -m app.cli gerar-propostas` (back com `HP_USE_MOCKS=false`).

## Atalhos

`A` aprova · `R` edita a classe · `J`/`K` próximo/anterior pendente · `↑`/`↓` linha anterior/seguinte · `Enter` expande · `/` busca · `Ctrl K` abrir paciente · `Esc` recolhe · `[` menu · `]` painel · `?` ajuda. Na faixa: setas, `+`/`-`, `C`, `Home` e Ctrl+roda.

O estado (filtros, página, paciente e, sem API, as decisões) fica salvo no navegador e na URL (`#/fila/SOL-...`).
