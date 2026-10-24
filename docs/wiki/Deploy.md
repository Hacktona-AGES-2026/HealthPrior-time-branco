# Deploy

Fonte: [`docs/deploy.md`](../deploy.md) (passo a passo completo). Decisão D-124.

```
Vercel (web/, estático)  ──VITE_API_URL──▶  Render (backend/Dockerfile)  ──DATABASE_URL──▶  Neon (Postgres)
```

O back vai como **contêiner** e não como função serverless, porque a publicação roda o verificador oficial como subprocesso, grava CSV
em disco e pode levar segundos.

| Peça | O que configurar |
|---|---|
| **Neon** | Projeto com Postgres; copiar a *connection string* (`postgresql://…?sslmode=require`). Não precisa criar tabelas |
| **Render** | Blueprint a partir do `render.yaml` (Docker, health check `/health`). Variáveis: `DATABASE_URL`, `HP_CORS_ORIGINS`, `NTFY_TOPIC` (opcional) |
| **Vercel** | Root Directory `web`; variável `VITE_API_URL` = URL do Render, sem barra no final (lida **na hora do build**) |

Depois de ter a URL da Vercel, coloque-a em `HP_CORS_ORIGINS` no Render (várias, separadas por vírgula). Sem isso o navegador bloqueia as
chamadas e o front cai nos dados de reserva.

## Primeira subida
O contêiner roda `python -m app.cli bootstrap`: com o banco vazio carrega o dataset, publica a fila pelo verificador oficial e semeia as
propostas de regra da demo (`HP_DEMO_SEED`). Com dados, não faz nada; reiniciar não refaz a carga nem mexe em decisões.

## Operação
- **Acordar antes da apresentação:** no plano grátis o Render dorme após cerca de 15 minutos; abra `/health` antes. O Neon grátis também demora um pouco no primeiro acesso.
- **Zerar a demo:** no SQL Editor do Neon, `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` e reiniciar o serviço.
- **Atualizar a fila depois de uma mudança de regra:** `POST /admin/publicar-fila` (o `bootstrap` só age em banco vazio).
- **Disco efêmero:** o CSV em `backend/output/` some a cada deploy; a fila publicada está no banco e `GET /fila/export` a gera de novo.
- **Segredos:** `DATABASE_URL` e tokens nunca vão para o git; se vazarem, gere nova senha no Neon e atualize o Render.
