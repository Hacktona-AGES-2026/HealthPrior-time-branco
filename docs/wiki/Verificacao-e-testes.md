# Verificação e testes

## Verificador oficial
`src/verificar_fila_priorizada.py` veio com o dataset do desafio e é a ferramenta de autoconferência da equipe.
Confere:
1. **Formato:** colunas `solicitacao_id`, `posicao`, `justificativa`; posições inteiras e únicas; ids existentes.
2. **Cobertura:** quantas solicitações ficaram de fora (legítimo para duplicatas e desistências, explicado em `DECISOES.md`).
3. **Regra de ouro:** nenhum paciente com CID `C*` abaixo de um paciente sem urgência clínica. A definição do
   verificador é conservadora: CID não oncológico, dor EVA ≤ 3, limitação nenhuma ou leve, sem CID de urgência,
   sem evento de piora e sem palavra de alarme na justificativa.
4. **Indicadores informativos:** posição mediana dos oncológicos, piora recente na primeira metade etc.

```bash
python src/verificar_fila_priorizada.py caminho/para/fila_priorizada.csv
```
Com a fila publicada: `curl https://SEU-BACK/fila/export -o fila.csv` e rode o comando acima sobre ele.
Resultado esperado: `RESULTADO: OK — regra de ouro respeitada e formato válido`.

O verificador também é **portão de publicação** (I-07): a API o executa antes de publicar e, se reprovar, mantém a fila anterior.

## Testes automatizados
- **Domínio puro** (regra de ouro, CID, urgência, SWALIS, negação): sem banco nem servidor.
- **Aplicação e infraestrutura:** casos de uso e repositórios contra Postgres real, incluindo carga, resolução de
  pendência e publicação com o verificador oficial.
- **API:** contrato de cada rota e erros.
- **Arquitetura:** `tests/test_arquitetura.py` falha se uma camada importar o que não pode.
- **CI** (`.github/workflows`): roda a suíte do back a cada PR e a cada push na `main`.

## Revisão de invariantes
Mudanças que mexem em classe, status da fila, camadas ou oncológicos devem passar pela revisão do `guardiao-invariantes`
(I-01 a I-10) e declarar no PR se isso foi feito. O repositório também traz as skills `verificar-fila`, `registrar-decisao` e `tarefa` e o agente `analista-dados` em `.claude/`.
