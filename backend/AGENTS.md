# AGENTS.md — backend

> Complementa o `AGENTS.md` da raiz. Não repita regras gerais aqui.

## Stack
- Python 3.9+ · FastAPI · SQLAlchemy 2 · PostgreSQL 16 (Docker) · psycopg 3
- Sem ORM de alto nível nem migrations (D-14, D-15): `Base.metadata.create_all`.

## Como rodar
```bash
docker compose up -d --wait                 # na raiz do repo: sobe o Postgres
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.cli carga           # carga inicial (idempotente)
.venv/bin/uvicorn app.main:app --reload     # API em :8000, docs em /docs
```
Config por variável de ambiente (defaults batem com o `docker-compose.yml`): `DATABASE_URL`, `DATA_DIR`.
Mudou o schema? `docker compose down -v` na raiz e rode a carga de novo.

## Como testar
```bash
cd backend && .venv/bin/python -m pytest
```
Só `tests/test_preprocessing.py` roda sem banco (`pytest tests/test_preprocessing.py`). Os de
integração usam o banco `healthprior_test` no mesmo Postgres (criado na primeira execução) e
pulam com aviso se o Postgres estiver fora do ar.

## Estrutura
```
backend/
  app/
    config.py   DATABASE_URL, DATA_DIR, REF
    models.py        tabelas (colunas dos CSVs com o nome original + estado do sistema + *_norm)
    db.py            engine e create_all
    loader.py        carga dos CSVs (upsert por chave primária, uma transação)
    preprocessing.py regras PRE-01..04 como funções puras (sem banco)
    normalization.py aplica o pré-processamento no banco e refaz o correcoes_log
    cli.py           python -m app.cli carga | normalizar
    main.py          FastAPI (POST /admin/carga)
  tests/             test_preprocessing (unitário, sem banco); test_carga e test_normalizacao
                     (integração, dataset real)
```

## Componentes implementados aqui
| Componente | Arquivo(s) |
|---|---|
| C-02 Ingestão (US-01) | `app/loader.py`, `app/models.py`, `app/cli.py` |
| C-05 Pré-processamento, PRE-01..04 (US-02) | `app/preprocessing.py`, `app/normalization.py` |

## Convenções locais
- Colunas dos CSVs entram com o nome e o valor originais (vazio vira NULL). Normalização entra
  como **colunas novas** (US-02); nunca sobrescreva a original.
- Colunas de estado do sistema (`info={"sistema": True}` no model: `classe_status`, `status_fila`,
  `*_norm`) não vêm do CSV e a carga não as escreve. As `*_norm` só mudam pela normalização.
- Regra nova de pré-processamento: função pura em `preprocessing.py` + teste unitário; a coluna
  nova entra no model e o log segue a D-17.
- Erros da API no formato `{"erro": "<CODIGO>", "mensagem": "..."}`.
