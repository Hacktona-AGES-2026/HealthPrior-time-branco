# SWALIS por regras (SW-01..SW-04)

Implementa o contrato C-07 (`docs/fluxo-sistema.md`). Código: `backend/app/domain/swalis.py` (regras),
`domain/texto.py` (negação), `infrastructure/swalis_regras.py` (composição) e
`infrastructure/llm_openrouter.py` (extração por LLM).

## Fluxo

```
justificativa_clinica + observacoes
   ├─ palavra-chave com negação (sempre)          → SinalTexto(origem="regra")  → muda a classe
   └─ LLM Jev via OpenRouter (opcional, em cache) → SinalTexto(origem="llm")    → só ALERTA
        só entra se o trecho existe LITERALMENTE no texto, não está negado
        e a palavra-chave ainda não pegou
eixo_progressao(CID, eventos, sinais) → 0..3
eixo_sintoma(CID, dor, limitação, sinais) → 0..2
cruzar_eixos → A1..D   (score = % do prazo consumido, como no stub)
```

O LLM **extrai e cita**; não devolve classe e seus sinais **não mudam a classe** (I-05): a categoria
do sinal vem do LLM, então usá-la na tabela seria o LLM decidindo. Os alertas aparecem nos motivos
(`alerta_llm:<categoria>`) para o regulador decidir. A classe sai da tabela abaixo e continua
`sugerida_nao_confirmada` até o regulador decidir (I-04).

## SW-01 · Eixo de progressão

| Nível | Quando |
|---|---|
| 3 | CID de obstrução/instabilidade (K40.0, K40.3, K42.0, K43.0, N13.2, I20.0) ou sinal `risco_vida` no texto |
| 2 | CID C* (exceto C44) ou biópsia positiva |
| 1 | Lesão incerta (D37–D48, R91), carcinoma de pele (C44) ou sinal `suspeita_malignidade` |
| 0 | Nenhum risco de progressão registrado |

## SW-02 · Eixo de sintoma

| Nível | Quando |
|---|---|
| 2 | Dor 7–10, limitação grave, CID com complicação (I83.2, K80.0) ou sinal `sintoma_grave` |
| 1 | Dor 4–6 ou limitação moderada; também quando dor **ou** limitação está vazia |
| 0 | Dor 0–3 e limitação nenhuma/leve |

## SW-03 · Tabela

| Progressão | Classe |
|---|---|
| 3 | A1 |
| 2 | A2 |
| 1 | B |
| 0 | sintoma 0 → D · 1 → C · 2 → B |

A justificativa mostra os dois eixos e o motivo de cada um.

## SW-04 · Negação

Termo precedido de "sem", "nega", "ausência de", "não há" ou "descarta" **na mesma oração** é ignorado.
A oração termina em `. ; : , ! ?` ou em "mas", "porém", "entretanto", "contudo", "evoluiu":
"Sem melhora, evoluiu com suboclusão" mantém a suboclusão. Testado nas 10 hérnias K40.9 do dataset
com "Sem sinais de encarceramento" (`tests/domain/test_swalis.py`).

## LLM (Jev 1.14)

- Modelo `typesafe/jev-1.14` (OpenRouter). É um modelo de **decisões**: não escreve texto e não
  funciona em `/chat/completions`. Usa `POST https://openrouter.ai/api/alpha/decisions` com
  `{model, state, questions}`; cada pergunta é `choice` e volta com `probabilities`.
- Como usamos: o texto é dividido em frases (`domain/texto.frases`) e, para cada frase, o Jev escolhe
  `risco_vida`, `suspeita_malignidade`, `sintoma_grave` ou `nenhum`. Vira alerta se a probabilidade
  for ≥ 0,7 (`PROB_MINIMA`), a frase não estiver negada, a palavra-chave ainda não tiver pegado e
  não for redundante (`suspeita_malignidade` em quem já tem CID C* é descartada).
  A citação é a própria frase, então é literal por construção.
- Configuração: `OPENROUTER_API_KEY` no `.env` da raiz (chave de **API**; chave de gerenciamento dá
  401); `HP_LLM_MODEL`, `HP_LLM_ENABLED`, `HP_LLM_CACHE`.
- Cache: `data/processed/cache_llm.json` (chave = modelo + versão das perguntas + texto). Com o cache,
  roda sem chave e sem rede. Pré-aqueça com `cd backend && python -m app.cli extrair-sinais`
  (887 textos em ~40 s, custo de centavos).
- Falha de rede/modelo: segue só com palavra-chave (nunca derruba a fila).
- A geração da fila lê **só o cache** (não chama a rede): saída reproduzível. Só `extrair-sinais` chama o LLM.
- Resultado no dataset (2026-10-24): alertas em 215 solicitações (risco_vida 102, suspeita_malignidade
  43, sintoma_grave 108); 63 alertas de risco de vida fora de A1 (ex.: SOL-2025-00216 bócio com
  desvio traqueal e dispneia, classe D; SOL-2026-00773 lesões coronárias >70% em 3 vasos, classe D).
- Concordância com a palavra-chave do verificador: o Jev marca 110/116 (95%) das frases com alarme e
  0/6 frases negadas. Amostra manual de 20 alertas extras (antes do filtro de redundância): ~7 úteis,
  ~10 redundantes (câncer já confirmado), ~3 exagerados (ex.: HPB com ITU de repetição como risco_vida).

## Questões abertas

| ID | Questão | Provisório |
|---|---|---|
| Q-SW1 | Termos de "suspeita de malignidade" (perda ponderal, crescimento rápido, linfonodo…) contam como progressão 1 ou 2? | 1 (igual a lesão incerta) |
| Q-SW2 | Eventos na espera (PS, internação, progressão em imagem, reavaliação com piora) devem subir o eixo de progressão? Hoje só definem a camada 2 | não sobem |
| Q-SW3 | Quais termos do verificador são `risco_vida` × `sintoma_grave`? (separação em `TERMOS`) | ver `domain/swalis.py` |
