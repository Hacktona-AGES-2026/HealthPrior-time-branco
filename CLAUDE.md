# CLAUDE.md

@AGENTS.md

## Específico do Claude Code

- Skills do projeto (use com `/`):
  - `/verificar-fila` — roda o verificador oficial e explica o resultado.
  - `/tarefa <C-xx ou descrição>` — fluxo planejar → implementar → testar → verificar.
  - `/registrar-decisao <decisão>` — adiciona entrada ao `DECISOES.md`.
- Subagentes:
  - `guardiao-invariantes` — revisa mudanças contra as invariantes I-01..I-10. Use antes de commitar qualquer coisa que mexa em ordenação, classe ou status.
  - `analista-dados` — investiga o dataset (somente leitura) e responde com números e IDs reais.
- Antes de editar vários arquivos, mostre o plano.
- Preferências locais (permissões pessoais) vão em `.claude/settings.local.json`, que não é commitado.
