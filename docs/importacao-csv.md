# Importar solicitações por CSV

Mostra que o sistema aceita pacientes novos: **uma linha ou várias**, pela tela **Importar** ou pela API.

## Como usar
1. Tela **Importar** (último item do menu) → **Baixar modelo** (cabeçalho completo + uma linha de exemplo).
2. Preencha. **Obrigatórias:** `solicitacao_id`, `paciente_id`, `nome_paciente`, `procedimento_id` (tem de existir no cadastro), `cid_principal`, `data_entrada_fila` (AAAA-MM-DD, não no futuro). As demais colunas do `fila_cirurgica.csv` são opcionais; `procedimento`, `especialidade` e `dias_em_fila` o sistema preenche.
3. Arraste o arquivo (ou cole o texto) e clique em **Importar**. Aceita `,` ou `;`, UTF-8 ou Latin-1.

```bash
curl -X POST -H "Content-Type: text/csv" --data-binary @novos.csv "http://localhost:8000/importacao/solicitacoes"   # ?publicar=false não republica
```

## O que acontece
- **Tudo ou nada:** o arquivo inteiro é validado antes de gravar. Qualquer erro devolve a lista (linha, campo, problema) e **nada é gravado**.
- **Quem já existe é ignorado**, nunca sobrescrito (I-10); aparece em "já existiam".
- **Mesmo caminho da carga:** normalização, flags, alertas, pendências e suspensão (uma linha com "operou pelo convênio" entra suspensa, com pendência bloqueante). A classe sugerida passa pelo Inbox como qualquer outra.
- **Fila republicada** e verificada (I-07). O verificador oficial só conhece os ids do CSV oficial, então ele roda sobre uma cópia temporária com as importadas (D-123).
- **Limites:** 2 MB e 5000 linhas por arquivo. Só solicitações (sem eventos nem procedimentos).

## Para a demonstração
Não é para importar ao vivo: a tela existe para mostrar que dá. Se for abrir, use o modelo com 1 ou 2 linhas.
