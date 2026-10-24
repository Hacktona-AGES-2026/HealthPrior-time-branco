# Deploy: front na Vercel, back no Render, banco no Neon

```
Vercel (web/, estático)  ──VITE_API_URL──▶  Render (backend/Dockerfile)  ──DATABASE_URL──▶  Neon (Postgres)
```

O front é só arquivos estáticos (Vite). O back precisa de processo comum (a publicação da fila roda o verificador oficial
como subprocesso, grava CSV em disco e pode levar segundos), por isso vai como contêiner e não como função serverless.

## 1. Banco: Neon
1. Crie um projeto em neon.tech (grátis) e copie a **connection string** (`postgresql://usuario:senha@host/db?sslmode=require`).
2. Não precisa criar tabelas: o back cria e carrega tudo na primeira subida.

## 2. Back: Render
1. Render, **New**, depois **Blueprint**, e escolha este repositório: ele lê o `render.yaml` (serviço `healthprior-api`, Docker).
2. Preencha as variáveis marcadas como secretas:
   - `DATABASE_URL`: a string do Neon (aceita `postgres://` e `postgresql://`).
   - `HP_CORS_ORIGINS`: deixe vazio por enquanto (passo 4).
   - `NTFY_TOPIC`: opcional (avisos de demonstração; veja `docs/notificacoes-demo.md`). Para ligar, troque `HP_NOTIFICA_CANAL` para `ntfy`.
3. No primeiro deploy, o contêiner roda `python -m app.cli bootstrap`: banco vazio, então carrega o dataset (941 solicitações), publica a fila (900, verificador oficial) e semeia as propostas de regra da demo (`HP_DEMO_SEED=true`). Nas próximas subidas ele vê dados e não faz nada.
4. Confira `https://SEU-SERVICO.onrender.com/health`: `{"status":"ok","mocks":false,...}`.

## 3. Front: Vercel
1. Vercel, **Add New**, depois **Project**, importe este repositório.
2. **Root Directory:** `web`. O resto (Vite, `npm ci`, `npm run build`, saída `dist`) já está no `web/vercel.json`.
3. **Environment Variables:** `VITE_API_URL` = a URL do back no Render (sem barra no final). É lida **na hora do build**: se mudar, faça um novo deploy.
4. Deploy. A URL final é do tipo `https://healthprior-xxxx.vercel.app`.

## 4. Fechar o ciclo (CORS)
No Render, defina `HP_CORS_ORIGINS` = a URL de **produção** da Vercel (ex.: `https://healthprior-xxxx.vercel.app`; vários separados por vírgula) e salve (o serviço reinicia). Sem isso o navegador bloqueia as chamadas do front ao back. As URLs de *preview* da Vercel têm outro domínio e não passam por esta lista.

## Antes da apresentação
- **Acorde o back:** no plano grátis o Render dorme após ~15 min sem uso; a primeira chamada leva de 30 a 60 s. Abra `/health` uns minutos antes (ou deixe um monitor gratuito, como o UptimeRobot, chamando `/health` a cada 5 min).
- O Neon grátis também "dorme": a primeira consulta depois de parado leva cerca de 1 s a mais.
- **Zerar a demo:** no SQL Editor do Neon rode `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` e reinicie o serviço no Render (o bootstrap recarrega tudo). Aprovações, importações e avisos feitos na demo ficam no banco até lá.
- O disco do Render é efêmero: o CSV da fila em `backend/output/` some a cada deploy, mas a fila publicada está no banco e `GET /fila/export` o gera de novo.

## Local com Docker (o mesmo contêiner do deploy)
```bash
docker build -f backend/Dockerfile -t healthprior-api .
docker run -p 8000:8000 -e DATABASE_URL=postgres://healthprior:healthprior@host.docker.internal:5432/healthprior healthprior-api
```
