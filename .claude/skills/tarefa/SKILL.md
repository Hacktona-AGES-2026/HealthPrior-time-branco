---
name: tarefa
description: Executa uma tarefa de desenvolvimento do HealthPrior seguindo o fluxo planejar, implementar, testar e verificar, ancorada nos componentes C-xx de docs/fluxo-sistema.md.
argument-hint: [C-xx ou descrição da tarefa]
disable-model-invocation: true
---

Tarefa: $ARGUMENTS

Siga este fluxo, sem pular etapas:

1. **Contexto.** Leia em `docs/fluxo-sistema.md` o componente relacionado (C-xx), as invariantes (§9), as decisões (§10) e as questões abertas (§11). Se a tarefa não corresponde a nenhum componente ou depende de uma questão aberta, pare e pergunte.
2. **Plano.** Em até 8 linhas: o que muda, arquivos afetados, como testar. Se tocar mais de 3 arquivos ou mudar a ordenação, mostre o plano e espere OK.
3. **Implementação mínima.** Sem abstrações extras. Respeite `AGENTS.md` (idioma, REF=2026-10-23, nada é apagado, CID e não flag).
4. **Teste.** Use casos reais do dataset (exemplos da §7 do fluxo). Para pipeline de dados, um teste com pytest ou um script de checagem com asserts basta.
5. **Verificação.** Se a ordenação, a classe ou o status de pacientes podem ter mudado, gere o `fila_priorizada.csv` e rode `/verificar-fila`. Peça ao subagente `guardiao-invariantes` para revisar o diff.
6. **Fechamento.** Atualize docs se o comportamento mudou; registre decisão nova com `/registrar-decisao`; sugira a mensagem de commit no formato `tipo(C-xx): descrição`.

Responda ao final com: o que foi feito, como foi testado, resultado do verificador (se aplicável) e pendências.
