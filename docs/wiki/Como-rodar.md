# Como rodar

Fonte: [`backend/AGENTS.md`](../../backend/AGENTS.md), [`web/README.md`](../../web/README.md) e [`.env.example`](../../.env.example).

## Pré-requisitos
Docker (Postgres 16), Python 3.10+ (a CI usa 3.12) e Node 22 para o front.

## Back
```bash
docker compose up -d --wait                 # Postgres (raiz do repositório)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.cli init-db                   # cria as tabelas
python -m app.cli carga                     # carga + normalização (941 solicitações)
python -m app.cli gerar-fila                # gera do banco, roda o verificador e publica (exit 1 se reprovar)
HP_USE_MOCKS=false uvicorn app.main:app --reload   # API em http://localhost:8000 (docs em /docs)
```
`python -m app.cli bootstrap` faz carga e fila só quando o banco está vazio (é o que o contêiner de deploy roda).
Sem `HP_USE_MOCKS=false` a API responde com dados de mentira, útil para o front trabalhar sem banco.

Comandos úteis: `normalizar`, `flags`, `bloqueantes`, `inconsistencias`, `extrair-sinais`, `sugerir-cid`,
`seed-aprendizado` e `gerar-propostas` (lista completa em `backend/AGENTS.md`).

## Front
```bash
cd web
npm install && npm run dev                  # http://localhost:5173
npm run build
npm run gen:api                             # regenera src/api/schema.ts com o back no ar
```
`VITE_API_URL` aponta para a API (padrão `http://127.0.0.1:8000`).

## Variáveis de ambiente (opcionais)
`HP_USE_MOCKS`, `HP_DB_URL` ou `DATABASE_URL`, `HP_CORS_ORIGINS`, `HP_REF_DATE`, `OPENROUTER_API_KEY` (LLM, só no `.env` da
raiz, nunca no git), `HP_NOTIFICA_CANAL` e as de notificação ([Notificações](Notificacoes.md)).
Segredos ficam no `.env` (ignorado pelo git); o `.env.example` lista os nomes.

## Testes
```bash
cd backend && pytest -q                     # inclui a guarda de arquitetura
pytest -q -n 4                              # em paralelo, um banco por worker
```
Os testes de banco usam o banco `healthprior_test` e são pulados se o Postgres estiver fora do ar.
