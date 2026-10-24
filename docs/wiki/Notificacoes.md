# Notificações ao paciente (demonstração)

Fonte: [`docs/notificacoes-demo.md`](../notificacoes-demo.md). Avisa quando o paciente muda de posição, quando a situação muda e
quando passa muito tempo sem evento. **Só para demonstração:** nada vai para o telefone de um paciente de verdade.

## Canais
| Canal | Quando usar |
|---|---|
| `simulado` (padrão) | Nada sai; a tela Notificações mostra o que seria enviado |
| `ntfy` | Push gratuito no celular, sem cadastro (recomendado para a demo) |
| `twilio` | SMS ou WhatsApp de conta de teste (opcional) |
| `waha` | WhatsApp não oficial, com chip descartável (opcional, perfil `whatsapp` do compose) |

`HP_NOTIFICA_CANAL` aceita vários canais separados por vírgula. Para o ntfy: `HP_NOTIFICA_CANAL=ntfy` e `NTFY_TOPIC` com um
nome **difícil de adivinhar** (no servidor público, o nome do tópico é o único controle de acesso).

## Como funciona
- A mudança grava a notificação na tabela `notificacoes` (status `pendente`), na mesma transação; um passo à parte envia.
- **Gatilhos:** posição (mudou `HP_NOTIFICA_MIN_POSICOES` ou mais, com teto `HP_NOTIFICA_MAX_POR_PUBLICACAO` por publicação), situação
  (decisão do regulador ou resolução de pendência bloqueante) e recontato (REC-01).
- **Texto genérico**, sem classe, score nem posição exata: só "subiu" ou "desceu", com o prefixo `[DEMO SOL-xxxx]`.
- Limite de envios por rodada (`HP_NOTIFICA_LIMITE_ENVIO`); falha de envio não derruba a decisão. `POST /notificacoes/enviar` reenvia as pendentes.

## Cuidados
Segredos (tokens do Twilio, chaves do WAHA) ficam só no `.env`. Um token colado em chat ou commit deve ser rotacionado.
