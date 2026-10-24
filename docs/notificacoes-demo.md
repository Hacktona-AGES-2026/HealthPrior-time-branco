# Notificações ao paciente (demonstração)

Avisa por SMS (Twilio, **conta de teste**) quando o paciente muda de posição, quando a situação muda e quando
está muito tempo sem evento (recontato). **Só para demonstração**: o destino é sempre um número da demo.

## Como funciona
- **Fila de saída:** a mudança grava a notificação (tabela `notificacoes`, status `pendente`) na mesma transação; um passo à parte envia.
- **Gatilhos:**
  - *posição:* depois de cada publicação da fila, quem mudou `HP_NOTIFICA_MIN_POSICOES` ou mais, as maiores mudanças primeiro, até `HP_NOTIFICA_MAX_POR_PUBLICACAO`;
  - *situação:* decisão do regulador confirmada (aprovar/editar/manter) e resolução de pendência **bloqueante**;
  - *recontato:* pendências `REC-01` abertas na atualização diária (no máximo o mesmo limite).
- **Texto genérico** ("Atualização da fila cirúrgica: …") (`domain/notificacoes.py`): sem classe, score nem posição exata, só "subiu" ou "desceu". Prefixo `[DEMO SOL-xxxx]` diz de qual paciente seria.
- **Segurança da demo:** canal `simulado` por padrão (nada sai). O Twilio só liga com `HP_NOTIFICA_CANAL=twilio` **e** credenciais **e** `HP_NOTIFICA_DESTINO`. Há limite de envios por rodada. Falha de envio não derruba a decisão nem a publicação: fica `falhou` e pode ser reenviada.
- **Conta de teste do Twilio:** só entrega a números verificados e acrescenta um aviso de "trial" à mensagem; o corpo sai sem acentos (cabe em SMS GSM-7).

## Ligar o Twilio
1. Crie a conta de teste em twilio.com, verifique o número do celular da apresentação e anote o Account SID, o Auth Token e o número de origem.
2. **Atenção ao tipo de credencial:** `TWILIO_ACCOUNT_SID` é sempre o Account SID (começa com `AC`, está na página inicial do console). Se você criou uma API Key (`SK...`), ela vai em `TWILIO_API_KEY_SID` e `TWILIO_API_KEY_SECRET`, e o `TWILIO_AUTH_TOKEN` pode ficar vazio.
3. No `.env` da raiz (não commitado; veja `.env.example`): `HP_NOTIFICA_CANAL=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `HP_NOTIFICA_DESTINO`.
3. Reinicie o back. A tela **Notificações** mostra "Twilio (conta de teste) → número mascarado".
4. Aprove ou edite um caso no Inbox: a mensagem chega no celular. `POST /notificacoes/enviar` reenvia as pendentes.

## ntfy.sh (push grátis, o caminho mais simples para a demo)
Sem cadastro e com texto livre (o texto genérico sai como está, com acentos). No celular, instale o app **ntfy** e assine o tópico.
1. `.env`: `HP_NOTIFICA_CANAL=ntfy` e `NTFY_TOPIC=<um nome difícil de adivinhar>` (no servidor público, o nome do tópico é o único controle de acesso; `NTFY_TOKEN` e `NTFY_URL` são opcionais).
2. Teste a assinatura (**sem espaço** depois da barra): `curl -d "oi" ntfy.sh/SEU-TOPICO`.
3. Aprove ou edite um caso no Inbox: chega o push "Atualizacao da fila cirurgica". Não usa telefone nem `HP_NOTIFICA_DESTINO`.

## SMS ao Brasil na conta de teste
A conta de teste só envia SMS ao Brasil com **modelos pré-definidos**; texto livre volta `400: Invalid template name`.
Defina `TWILIO_SMS_TEMPLATE=sms_event_notifications` (ou outro modelo da sua conta): o Body enviado passa a ser o nome do
modelo, e o Twilio entrega o texto dele. A tela Notificações continua mostrando o texto de verdade que seria enviado.
Em conta paga (ou com o remetente aprovado) deixe a variável vazia e o texto genérico sai como está.

## WhatsApp (sandbox do Twilio)
O remetente **não** é o seu número: é o número do sandbox do Twilio. O destino é o seu.
1. No console do Twilio: **Messaging**, depois **Try it out**, depois **Send a WhatsApp message**. Aparecem o número do sandbox (em geral `+1 415 523 8886`) e um código de adesão (`join palavra-palavra`).
2. No seu WhatsApp, mande esse `join ...` para o número do sandbox. A confirmação chega na hora.
3. `.env`:
   ```bash
   HP_NOTIFICA_CANAL=twilio
   TWILIO_FROM=whatsapp:+14155238886
   HP_NOTIFICA_DESTINO=+55SEUDDDSEUNUMERO
   ```
   O sistema acrescenta `whatsapp:` ao destino e mantém os acentos.
4. O sandbox só aceita texto livre por 24 h depois da última mensagem que **você** enviou a ele; passado esse prazo, mande qualquer mensagem de novo para reabrir. O `join` vale por alguns dias e pode ser refeito.

## Limites conhecidos
- Não é produção: não há consentimento do paciente, opt-out, nem telefone do paciente usado (LGPD).
- O WhatsApp real (produção) exige a API oficial, número aprovado e modelos de mensagem; aqui só o sandbox de teste.
