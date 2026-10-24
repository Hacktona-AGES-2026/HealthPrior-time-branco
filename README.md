# HealthPrior — Time Branco

Priorização inteligente da fila cirúrgica (Desafio 1 · 9ª Hackatona de Engenharia de Software 2026 · Fin-x · PUCRS · Hospital São Lucas). Dados 100% sintéticos.

## Estrutura

```
.
├── data/
│   ├── fila_cirurgica.csv        # fila: uma linha por solicitação
│   ├── eventos_clinicos.csv      # eventos durante a espera
│   ├── procedimentos.csv         # catálogo de procedimentos
│   ├── referencias/
│   │   ├── swalis.csv            # classes de urgência (referência)
│   │   └── CID10CSV/             # tabelas CID-10 (DATASUS)
│   └── processed/
│       └── score_mortalidade.csv # saída de score_mortalidade.py
├── src/
│   ├── score_mortalidade.py          # score de mortalidade por solicitação
│   └── verificar_fila_priorizada.py  # verificador do entregável
└── docs/
    ├── fluxo-sistema.md      # documentação do fluxo do sistema
    ├── dataset-readme.md     # README original do dataset
    └── dicionario_dados.md   # dicionário de dados
```

## Uso

```bash
python src/score_mortalidade.py                      # gera data/processed/score_mortalidade.csv
python src/verificar_fila_priorizada.py fila_priorizada.csv
```

## Documentação e desenvolvimento com IA

- Wiki do projeto (visão geral, regras, API, deploy): [`docs/wiki/Home.md`](docs/wiki/Home.md)
- Fluxo do sistema: [`docs/fluxo-sistema.md`](docs/fluxo-sistema.md)
- Decisões e exclusões (entregável): [`DECISOES.md`](DECISOES.md)
- Instruções para agentes de IA (Claude Code, Cursor, Codex, Copilot): [`AGENTS.md`](AGENTS.md)
