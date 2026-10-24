# HealthPrior · protótipo de regulação da fila cirúrgica

Front-end only (Vite + React + TypeScript + Tailwind v4 + shadcn/ui). Todos os dados são fictícios e ficam em `src/data`.

## Como rodar

```bash
npm install && npm run dev
npm run build
```

## Dados: API real (padrão) ou mock

- O front lê a fila publicada do backend: `GET /fila` (todas as páginas) + `GET /inbox`, em `src/data/fila.ts` (`carregarFila`).
  O adaptador `src/data/adaptador.ts` converte cada item no tipo `Paciente`.
- URL da API: `VITE_API_URL` (padrão `http://127.0.0.1:8000`). Suba o back antes: `cd backend && uvicorn app.main:app` com `HP_USE_MOCKS=false`, carga e fila publicada.
- Sem API, o front cai nos dados de exemplo de `src/data` e mostra um aviso.
- Ações: **Aprovar** → `POST /decisoes` (`aprovar`); **Rejeitar** → `POST /decisoes` (`editar`, com classe, motivo codificado e justificativa); **Registrar evento** → `POST /eventos`. Depois de cada ação a fila é recarregada.
- Página **Inbox**: propostas do SWALIS que aguardam um profissional (classe atual → sugerida).
- Ficha com dados da API: `GET /solicitacoes/{id}` mostra a explicação, os motivos do SWALIS (com origem: palavra-chave ou Jev p=…), a linha do tempo de eventos, as decisões do regulador e as pendências. O que a API não expõe (confiança, ASA, HbA1c, pré-operatório, gráficos da IA) fica escondido.

## Atalhos

`A` aprova · `R` rejeita · `J`/`K` próximo/anterior pendente · `Esc` recolhe · `[` menu lateral · `?` ajuda.
