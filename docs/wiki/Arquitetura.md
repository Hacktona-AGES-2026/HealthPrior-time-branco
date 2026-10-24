# Arquitetura

Fonte: [`docs/arquitetura-backend.md`](../arquitetura-backend.md) e [`backend/AGENTS.md`](../../backend/AGENTS.md).

```
Navegador ──▶ web/ (Vite + React)  ──HTTP──▶  backend/ (FastAPI)  ──▶  PostgreSQL 16
                                                    │
                                                    └─▶ src/verificar_fila_priorizada.py (portão de publicação)
```

## Back (`backend/`)
Python 3.10+ (a CI usa 3.12), FastAPI, SQLModel/SQLAlchemy 2, PostgreSQL 16, psycopg 3, pytest. **Clean Architecture
enxuta**, com dependência em um só sentido:

| Camada | Conteúdo | Pode importar |
|---|---|---|
| `domain/` | Regras puras: CID, urgência, SWALIS, ranking, pendências, entidades e *ports* | só a biblioteca padrão |
| `application/` | Casos de uso (um arquivo por caso) | `domain` |
| `infrastructure/` | Postgres, CSV, verificador oficial, LLM, notificador | `domain` e bibliotecas técnicas |
| `api/` | Rotas, schemas, injeção de dependência manual (`deps.py`) | tudo (é a borda) |

`tests/test_arquitetura.py` lê os imports e **falha** se a regra de dependência for quebrada. O domínio puro permite
testar a regra de ouro sem banco nem servidor.

Os roteadores mantêm um ramo de mocks (`HP_USE_MOCKS`, padrão `true`) para o front trabalhar sem banco; o deploy usa `false`.
Toda operação que altera estado confirma a transação primeiro e só então republica a fila; se o verificador reprovar,
a decisão vale e a fila anterior continua publicada (resposta com `fila_publicada=false`).

## Front (`web/`)
Vite, React 19, TypeScript, Tailwind v4, shadcn/ui (Base UI) e store em zustand. A navegação usa rotas por hash
(`#/fila`, `#/propostas`…). Os tipos da API são **gerados** do OpenAPI (`npm run gen:api` grava `src/api/schema.ts`).
Se a API estiver fora do ar, o front mostra um aviso e lê dados de reserva dos CSVs, somente leitura. Telas do menu: Fila, Inbox, Pacientes
(ficha com a explicação da posição), Análise, SWALIS, Pendências, Propostas, Notificações e Importar.

## Dados
`data/` tem a fila (`fila_cirurgica.csv`), os eventos, os procedimentos e as referências (SWALIS e CID-10). A primeira subida
carrega o dataset no banco (`python -m app.cli bootstrap`). Dicionário: [`docs/dicionario_dados.md`](../dicionario_dados.md).
