# Decisões

Toda decisão que muda comportamento, regra clínica, contrato ou escopo é registrada em [`DECISOES.md`](../../DECISOES.md), na raiz.

## Formato
Uma linha por decisão, com `ID` (`D-nn`), data, a decisão, o **motivo**, a **alternativa descartada** e o componente ou a user story.
O arquivo também lista as solicitações que ficaram fora do `fila_priorizada.csv` e por quê (entregável do desafio).

## Como registrar
1. Use o próximo número livre. A numeração é compartilhada entre branches: se duas branches pegarem o mesmo número, a que
   entrar depois **renumera as suas linhas** ao resolver o conflito.
2. Escreva o motivo e a alternativa descartada, não só o que foi feito.
3. Mudou uma decisão antiga? Risque a anterior e aponte a nova (por exemplo D-06, revista por D-112).
4. Decisão que afeta a regra de ouro ou as invariantes passa pelo `guardiao-invariantes`.
5. A skill `registrar-decisao` (em `.claude/skills/`) ajuda a manter o formato.

## Algumas decisões estruturais
| ID | Resumo |
|---|---|
| D-01 | Carga inicial não passa pelo regulador; classe fica "sugerida, não confirmada" |
| D-05 | Inconsistências são sinalizadas, nunca apagadas |
| D-06 / D-112 | Regra de ouro como camadas (1 e 2 num bloco só), não como peso |
| D-07 | O verificador é portão de publicação |
| D-08 | O aprendizado propõe, o comitê aprova, as regras têm versão |
| D-14 / D-15 | Clean Architecture enxuta; PostgreSQL 16 no lugar do SQLite |
| D-124 | Deploy: Vercel + Render (contêiner) + Neon |
