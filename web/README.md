# HealthPrior · protótipo de regulação da fila cirúrgica

Front-end only (Vite + React + TypeScript + Tailwind v4 + shadcn/ui). Todos os dados são fictícios e ficam em `src/data`.

## Como rodar

```bash
npm install && npm run dev
npm run build
```

## Pendências (US-06): primeira tela ligada à API

A página **Pendências** lê `GET /pendencias` do back; o resto do protótipo continua com dados fictícios.

```bash
# back (na pasta backend/): HP_USE_MOCKS=false mostra os dados reais da carga
docker compose up -d --wait && python -m app.cli carga
HP_USE_MOCKS=false uvicorn app.main:app

# front: a URL da API vem de VITE_API_URL (padrão http://localhost:8000; veja .env.example)
npm run dev
```

Com `HP_USE_MOCKS=true` (padrão do back) a API devolve uma pendência fixa só para desenvolver a tela.

Os tipos da API são **gerados**, não escritos à mão: com o back no ar, `npm run gen:api` atualiza `src/api/schema.ts`
(`OPENAPI_URL=... npm run gen:api` para outra URL). Mudou o contrato? Rode o comando e commite o arquivo gerado.
O gerador roda via `npx` (versão fixa) porque exige TypeScript 5 e este projeto usa o 6 (D-60).

## Trocar o mock por dados reais

- O tipo `Paciente` está em `src/data/tipos.ts`.
- `src/data/fila.ts` exporta `PACIENTES`, `FANTASMAS`, `FILA`, `TOTAL_FILA` e `PACIENTE_POR_ID`. Substitua a construção de `pacientes` (hoje `gerarPacientesBase()` em `src/data/gerador.ts`) por um array de `Paciente` vindo da saída do algoritmo; o resto do app lê só esses exports.
- `FANTASMAS` são as posições sem detalhe (barras cinza da faixa); `BANDAS` define em que posições cada classe começa e termina.

## Atalhos

`A` aprova · `R` rejeita · `J`/`K` próximo/anterior pendente · `Esc` recolhe · `[` menu lateral · `?` ajuda.
