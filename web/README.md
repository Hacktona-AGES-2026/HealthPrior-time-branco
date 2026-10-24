# HealthPrior · protótipo de regulação da fila cirúrgica

Front-end only (Vite + React + TypeScript + Tailwind v4 + shadcn/ui). Todos os dados são fictícios e ficam em `src/data`.

## Como rodar

```bash
npm install && npm run dev
npm run build
```

## Trocar o mock por dados reais

- O tipo `Paciente` está em `src/data/tipos.ts`.
- `src/data/fila.ts` exporta `PACIENTES`, `FANTASMAS`, `FILA`, `TOTAL_FILA` e `PACIENTE_POR_ID`. Substitua a construção de `pacientes` (hoje `gerarPacientesBase()` em `src/data/gerador.ts`) por um array de `Paciente` vindo da saída do algoritmo; o resto do app lê só esses exports.
- `FANTASMAS` são as posições sem detalhe (barras cinza da faixa); `BANDAS` define em que posições cada classe começa e termina.

## Atalhos

`A` aprova · `R` rejeita · `J`/`K` próximo/anterior pendente · `Esc` recolhe · `[` menu lateral · `?` ajuda.
