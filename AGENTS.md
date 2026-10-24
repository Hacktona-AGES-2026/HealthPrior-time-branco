# AGENTS.md — HealthPrior (Time Branco)

Instruções para **qualquer agente de IA** (Claude Code, Cursor, Codex, Copilot…) e para humanos.
Contexto: **hackathon de ~20h**. Priorize algo que funcione na demo, com segurança, sobre arquitetura perfeita.

## O que é o projeto

Priorização inteligente da fila de cirurgias eletivas (Desafio 1 · Fin-X · PUCRS · HSL).
Entrada: dataset sintético (data de referência **23/10/2026**). Saída obrigatória: `fila_priorizada.csv`
(`solicitacao_id`, `posicao`, `justificativa`), validada por `src/verificar_fila_priorizada.py`.

**Fonte de verdade do comportamento:** `docs/fluxo-sistema.md`. **O que construir:** `docs/user-stories.md` (US-xx, prioridades P0/P1/P2, divisão back × front e contrato da API). **Como o backend é organizado:** `docs/arquitetura-backend.md` (camadas, regra de dependência, receitas). Leia as seções 9 (invariantes), 10 (decisões) e 11 (questões abertas) antes de codar.

## Prazos

- `fila_priorizada.csv` pronto: **sáb 24/10 14h**
- Repositório final: **sáb 24/10 18h**
- Pitch (5 min): **sáb 24/10 19h**

## Regras inegociáveis (resumo de `docs/fluxo-sistema.md` §9)

1. **Regra de ouro:** paciente com CID iniciado por `C` (após normalizar: maiúsculo, sem ponto) **nunca** fica abaixo de paciente sem urgência clínica. Use o **CID, nunca `flag_oncologico`**.
2. Fila que não passa em `src/verificar_fila_priorizada.py` **não é entregue/publicada**.
3. **Nada é apagado** do dataset: use status (`ativa`/`suspensa`/`removida`) + motivo.
4. Mudança de classe exige decisão humana (exceto carga inicial, marcada como não confirmada).
5. LLM **extrai e cita** trechos; nunca decide classe nem altera CID sozinho.
6. Eventos anteriores à entrada na fila são histórico, não piora.
7. HbA1c, ASA, distância, faltas e quantidade de eventos **não** entram no score (são alertas/auditoria).
8. Não invente regra clínica. Se não está documentado, é questão aberta: deixe configurável e registre.

## Mapa do repositório

```
data/                      dados oficiais do desafio (somente leitura)
  fila_cirurgica.csv       941 solicitações
  eventos_clinicos.csv     ~1.500 eventos
  procedimentos.csv        23 procedimentos
  referencias/swalis.csv   classes A1–D e prazos
  referencias/CID10CSV/    tabelas CID-10 do DATASUS
  processed/               saídas geradas (ex.: score_mortalidade.csv)
src/
  verificar_fila_priorizada.py   verificador oficial (não editar a lógica; lê data/ por padrão)
  score_mortalidade.py           score de comorbidade (Charlson/Elixhauser) — contexto, não ordena a fila
docs/
  fluxo-sistema.md         fluxo do sistema, componentes C-xx, invariantes I-xx, decisões D-xx
  user-stories.md          histórias US-xx, divisão back × front, contrato da API
  arquitetura-backend.md   Clean Architecture do backend: camadas, dependências, receitas
  dataset-readme.md        README original do dataset (enunciado, entregável)
  dicionario_dados.md      descrição das colunas
  templates/               modelos (ex.: AGENTS.md de módulo)
  (swalis.md)              a criar: regras internas do SWALIS
DECISOES.md                decisões e exclusões (entregável)
backend/                   API FastAPI + pipeline (Clean Architecture) — ver backend/AGENTS.md
frontend/                  a criar — tem seu próprio AGENTS.md
.claude/                   skills e subagentes do Claude Code
```

Ao criar uma pasta de módulo (`backend/`, `frontend/`, `pipeline/`…), crie junto um `AGENTS.md` curto com: stack, como rodar, como testar e convenções locais (use `docs/templates/AGENTS-modulo.md`). Crie também um `CLAUDE.md` contendo só `@AGENTS.md`, para o Claude Code carregar. Não repita o que está aqui.

## Stack e comandos

- **Back:** Python + **FastAPI** + **PostgreSQL 16** (Docker, SQLModel/SQLAlchemy 2) + pandas no pipeline. Pasta `backend/` (ver `backend/AGENTS.md`).
- **Front:** **React** (Vite + TypeScript). Pasta `frontend/`. Tipos da API gerados do OpenAPI do FastAPI.
- **Fronteira:** o back é dono de toda regra de negócio; o front só exibe e coleta decisões (ver `docs/user-stories.md` §1 e §5). Sem login: seletor de persona no front.

> Comandos de teste/execução: preencher quando `backend/` e `frontend/` forem criados (e nos `AGENTS.md` de cada pasta).

| O quê | Comando |
|---|---|
| Verificar a fila | `python src/verificar_fila_priorizada.py <caminho>/fila_priorizada.csv` |
| Gerar a fila (provisório) | `cd backend && python -m app.cli gerar-fila-csv` (gera `backend/output/fila_priorizada.csv` e roda o verificador) |
| Score de mortalidade | `python src/score_mortalidade.py` (gera `data/processed/score_mortalidade.csv`) |
| Instalar deps (Python) | `pip install -r requirements.txt` |
| Subir o Postgres | `docker compose up -d --wait` |
| Carga inicial | `cd backend && python -m app.cli carga` |
| Testes (back) | `cd backend && pytest -q` |
| Rodar backend | `cd backend && uvicorn app.main:app --reload` (docs em `/docs`) |
| Rodar frontend | _a definir_ |

Dependência mínima de dados: `pandas` (o verificador usa).

## Como trabalhar (fluxo para agentes)

1. **Entenda a tarefa**: ache a história (`US-xx`) em `docs/user-stories.md` e o componente (`C-xx`) em `docs/fluxo-sistema.md`. Se não houver, pergunte antes de inventar.
2. **Planeje em poucas linhas** (o que muda, quais arquivos). Para mudanças grandes, mostre o plano antes de codar.
3. **Implemente o mínimo** que resolve, **na camada certa** (`docs/arquitetura-backend.md` §6). Sem abstrações "para o futuro".
4. **Teste com dados reais** do dataset. Os exemplos da §7 do fluxo (ex.: SOL-2023-00010, SOL-2025-00149, PAC-00151) são casos de teste prontos.
5. **Se mexeu na ordenação**, rode o verificador. Falhou = não terminou.
6. **Se tomou uma decisão** que não estava documentada, registre em `DECISOES.md` (skill `/registrar-decisao` no Claude Code).
7. **Atualize a documentação** no mesmo commit quando o comportamento mudar.

## Convenções

- Idioma: **nomes do domínio em português** (termos do dataset e do fluxo: `solicitacao`, `camada`, `pendencia`); termos técnicos genéricos podem ficar em inglês. Comentários, docs e mensagens de commit em português. Nomes de colunas do dataset ficam como estão.
- Commits: `tipo(escopo): descrição`, ex. `feat(C-05): normaliza CID sem ponto`, `fix(C-11): oncológico abaixo de não urgente`. Tipos: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.
- Branches curtas: `feat/<nome>`; PR pequeno e rápido. `main` sempre com fila válida.
- Datas sempre relativas a `REF = 2026-10-23`, nunca `today()`.
- Toda transformação de dados registra o valor original (não sobrescreve sem log).
- Segredos (chaves de LLM) só em `.env`, nunca no código ou no prompt commitado.

## Pragmatismo de hackathon

- Feito > perfeito. Hardcode é aceitável se estiver isolado e documentado.
- Prefira bibliotecas que o time já conhece.
- Resultados de LLM: **cachear** em arquivo para a demo não depender de rede.
- Não gaste tempo com: autenticação real, deploy complexo, cobertura de testes total. Gaste com: regra de ouro, explicação por paciente, demo.
- Cada pessoa trabalha num componente diferente para evitar conflito de merge.
