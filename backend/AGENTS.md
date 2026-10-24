# AGENTS.md — backend

> Complementa o `AGENTS.md` da raiz (regras, invariantes, convenções). Não repita aqui.
> **Arquitetura completa (camadas, fluxos, receitas, checklist):** `docs/arquitetura-backend.md`.

## Stack
Python 3.10+ · FastAPI · SQLModel + PostgreSQL 16 (Docker, D-15) · pandas (só em infraestrutura/pipeline) · pytest.

## Como rodar (dentro de `backend/`)
```bash
docker compose up -d --wait            # na raiz do repo: sobe o Postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # API em http://localhost:8000, docs em /docs
python -m app.cli init-db              # cria as tabelas
python -m app.cli carga                # US-01 + US-02 (carga e normalização, mesma transação)
python -m app.cli normalizar           # US-02: recalcula só as colunas *_norm e o correcoes_log
python -m app.cli flags                # US-03: recalcula oncologico/piora e marca eventos (sem recarregar)
python -m app.cli gerar-fila           # US-08/09/10 (via banco, após US-01)
python -m app.cli gerar-fila-csv       # fila direto do dataset + verificador (provisório, D-26)
pytest -q                              # testes (inclui guarda de arquitetura)
                                       # os de banco usam healthprior_test e pulam se o Postgres estiver fora
```
Variáveis (opcionais): `HP_USE_MOCKS` (padrão `true`), `HP_DB_URL` (padrão: o Postgres do docker-compose), `TEST_DATABASE_URL`, `HP_DATA_DIR`, `HP_OUTPUT_DIR`, `HP_REF_DATE`.

## Arquitetura (Clean Architecture enxuta)

```
app/
  domain/            REGRAS PURAS. Python puro: sem FastAPI, SQLModel, pandas.
    enums.py           vocabulário (Camada, Classe, StatusFila, MotivoCodificado…)
    models.py          entidades (dataclasses): Solicitacao, Evento, Pendencia, Decisao, ResultadoScore…
    errors.py          erros de domínio (ex.: OncologicoRebaixadoError -> 422)
    ports.py           interfaces (Protocol): repositórios, SwalisScorer, VerificadorFila
    cid.py             normalização e classificação de CID (I-09)
    urgencia.py        sinais de urgência (camada 2)
    ranking.py         trava da regra de ouro (US-08)
    preprocessing/     regras PRE-xx (US-02..05)
  application/       CASOS DE USO. Orquestram domínio + portas. Um arquivo por caso de uso.
    carga_inicial.py   US-01 (+ normalização na mesma transação, D-20)
    normalizar.py      US-02
    recalcular_flags.py US-03 (PRE-05..08; roda na carga, mesma transação, D-32)
    gerar_fila.py      US-08/09/10
    registrar_evento.py US-15
    decidir.py         US-13/14
    resolver_pendencia.py US-07
  infrastructure/    DETALHES. Implementam as portas.
    db.py, tables.py   Postgres/SQLModel (tabelas espelham fluxo-sistema.md §8)
    repositories.py    Sql*Repository (Table <-> entidade)
    csv_loader.py      leitura do dataset (CSV -> registros tipados; valores originais)
    swalis_stub.py     SWALIS provisório (troque pelo real em api/deps.py)
    verificador.py     chama src/verificar_fila_priorizada.py
    exportador.py      escreve fila_priorizada.csv
  api/               ENTRADA HTTP. Fina: valida, chama caso de uso, devolve schema.
    schemas.py         CONTRATO da API (= docs/user-stories.md §5)
    mocks.py           respostas fixas enquanto HP_USE_MOCKS=true
    deps.py            composição: único lugar que instancia implementações concretas
    errors.py          DomainError -> {"erro","mensagem"}
    routers/           um arquivo por recurso
  cli.py             comandos de linha (carga, normalizar, flags, gerar-fila, decisoes)
  config.py          configuração (REF_DATE fixa = 2026-10-23)
tests/               espelha app/ ; test_arquitetura.py protege a regra de dependência
```

**Regra de dependência** (verificada por `tests/test_arquitetura.py`):
`api → application → domain` e `infrastructure → domain`. **domain não importa ninguém**; application não importa infrastructure/api.

## Onde colocar cada coisa
| Vou… | Coloco em |
|---|---|
| Criar/alterar uma regra (PRE-xx, camada, CID) | `domain/` como função pura + teste em `tests/domain/` |
| Criar um fluxo que lê/grava e chama regras | `application/<caso_de_uso>.py` recebendo portas no `__init__` |
| Falar com banco, arquivo, LLM, subprocess | `infrastructure/` implementando um Protocol de `domain/ports.py` |
| Expor um endpoint | `api/routers/<recurso>.py` + schema em `api/schemas.py` |
| Trocar uma implementação (ex.: SWALIS real) | só `api/deps.py` (e `cli.py`) |

## Convenções locais
- Sem migrations (D-16): tabelas via `create_all`. Mudou o schema? `docker compose down -v` e rode a carga de novo.
- Carga (US-01): colunas dos CSVs entram com nome e valor originais (vazio vira NULL); normalização vai em colunas novas (US-02). A recarga não toca `classe_status`/`status_fila`. `eventos.solicitacao_id` sem FK (D-17).
- Transação: repositórios não confirmam; o caso de uso chama `UnidadeDeTrabalho.confirmar()/desfazer()` (carga + normalização entram juntas ou não entram).
- Flags (US-03): `oncologico` pelo CID (nunca pela flag) e `piora_recalculada` pelos eventos; eventos recebem `duplicado_de`/`historico` (nunca são apagados). As flags originais ficam intactas e cada divergência vai para `correcoes_log` (PRE-05/06).
- Regra nova de pré-processamento: função pura em `domain/preprocessing/` + teste em `tests/domain/`; coluna nova na tabela; log só para mudança de valor visível (D-18).
- Funções de domínio são **puras e determinísticas** (sem `date.today()`: use `settings.ref_date` passado de fora).
- Rotas não têm regra de negócio. Se aparecer um `if` de regra numa rota, mova para domain/application.
- Erros de regra: lance um `DomainError` específico; a API converte. `NotImplementedError` vira 501.
- Pandas só em `infrastructure/` (e scripts). O domínio trabalha com dataclasses.
- Mocks: quando implementar um endpoint de verdade, mantenha o mesmo schema e desligue o mock (`HP_USE_MOCKS=false`).
- Marque o que falta com `TODO(US-xx)` — `grep -rn "TODO(US-" app` mostra o backlog no código.
- Testes com IDs reais do dataset (exemplos em `docs/fluxo-sistema.md` §7 e `docs/user-stories.md`).

## Pragmatismo (hackathon)
- Sem camadas extras: nada de service locator, DI framework, DTO duplicado, repositório genérico.
- Repositórios só com os métodos que alguém usa.
- Se um caso de uso for trivial, ele pode chamar o domínio direto; a regra de dependência é o que não se negocia.
