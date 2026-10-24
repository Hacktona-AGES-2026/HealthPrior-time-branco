# Importação de CSV

Fonte: [`docs/importacao-csv.md`](../importacao-csv.md). Mostra que o sistema aceita pacientes novos, **uma linha ou várias**,
pela tela **Importar** (último item do menu) ou pela API. Não é para importar ao vivo na apresentação: a tela existe para
mostrar que dá.

## Como usar
1. Tela **Importar**, depois **Baixar modelo** (cabeçalho completo e uma linha de exemplo).
2. Preencha. Obrigatórias: `solicitacao_id`, `paciente_id`, `nome_paciente`, `procedimento_id` (precisa existir no cadastro),
   `cid_principal` e `data_entrada_fila` (AAAA-MM-DD, não no futuro).
3. Arraste o arquivo (ou cole o texto) e clique em **Importar**. Aceita `,` ou `;`, UTF-8 ou Latin-1.

```bash
curl -X POST -H "Content-Type: text/csv" --data-binary @novos.csv "http://localhost:8000/importacao/solicitacoes"   # ?publicar=false não republica
```

## O que acontece
- **Tudo ou nada:** o arquivo é validado inteiro antes de gravar; qualquer erro devolve a lista (linha, campo, problema) e nada é gravado.
- **Quem já existe é ignorado**, nunca sobrescrito (I-10).
- **Mesmo caminho da carga:** normalização, flags, alertas, pendências e suspensão. A classe sugerida passa pelo Inbox como qualquer outra.
- **Fila republicada e verificada** (I-07). O verificador oficial só conhece os ids do CSV oficial, então ele roda sobre uma cópia
  temporária que inclui as linhas importadas (D-123).
- **Limites:** 2 MB e 5000 linhas por arquivo; só solicitações (sem eventos nem procedimentos).
