# SWALIS por pontos + regras (SW-01..SW-04)

Implementa o contrato C-07 (`docs/fluxo-sistema.md`). Código: `backend/app/domain/swalis.py` (pontos e
regras), `domain/texto.py` (frases e negação), `infrastructure/swalis_regras.py` (composição) e
`infrastructure/llm_openrouter.py` (Jev).

## Fluxo em duas etapas

```
1. PONTOS (o que o paciente tem, cada um com evidência citada)
   campos      CID, dor EVA, limitação, eventos (biópsia)         → origem "campo/CID"
   palavra-chave com negação (justificativa + observações)       → origem "palavra-chave"
   Jev: para cada frase, qual ponto ela descreve (+ probabilidade) → origem "Jev p=0,98"
        frase literal (citação por construção), não negada
        p ≥ 0,7 conta · 0,4 ≤ p < 0,7 vai para "revisar" · p < 0,4 ignorado

2. DECISÃO (regras determinísticas)
   eixo de progressão = MAIOR nível entre os pontos de progressão (0..3)
   eixo de sintoma    = MAIOR nível entre os pontos de sintoma (0..2)
   tabela SWALIS → A1..D   (score = % do prazo consumido)
```

- **Rastreável:** cada motivo do eixo diz o ponto, a frase/campo e a origem. Ex.:
  `progressão 3: "Hernia irredutivel nas ultimas semanas" → obstrucao (Jev p=1.00)`.
- **O Jev só sobe, nunca baixa:** como o eixo é o máximo, sem o Jev a classe é a das regras; com ele,
  só pode ficar igual ou maior.
- **Quem decide é a tabela** e a classe continua `sugerida_nao_confirmada` até o regulador (I-04, I-05).
  Leitura da I-05 adotada (D-63): o Jev aponta e cita; "nunca decide classe sozinho" vale porque a
  classe sai da tabela **e** só vale depois de o regulador confirmar. Por isso a UI deve mostrar a origem
  ("Jev p=…") ao lado de cada ponto.
- Sem chave e sem cache, roda só com campos + palavra-chave (o comportamento anterior).

## Pontos

| Ponto | Eixo · nível | Palavra-chave | Jev (descrição enviada) |
|---|---|---|---|
| `obstrucao` | progressão 3 | encarcer, estrangul, suboclus | obstrução/risco de estrangulamento agora, hérnia irredutível, retenção urinária aguda |
| `risco_vida` | progressão 3 | colangite, icter, melena, sepse, transfund, síncope… | sangramento ativo/transfusão, sepse, colangite, angina instável, insuficiência respiratória, compressão de via aérea |
| `perda_funcao` | progressão 3 | hidronefrose, perda de função, glaucoma facomórfico, dano neurológico | risco de perda irreversível de órgão/função |
| `cancer_confirmado` | progressão 2 | — | câncer **do próprio paciente** confirmado por biópsia/AP (antecedente familiar e dado administrativo, como transporte/TFD, = `nenhum`) |
| `suspeita_malignidade` | progressão 1 | perda ponderal, disfagia, rouquidão, crescimento rápido… | suspeita de câncer ainda não confirmada |
| `dor_intensa` | sintoma 2 | — | dor intensa, incapacitante ou em repouso |
| `sintoma_grave` | sintoma 2 | acamad, úlcera de pressão, quedas de repetição | acamado, dependente, quedas, não anda |
| `sintoma_moderado` | sintoma 1 | — | dor/limitação moderada, baixa visão por catarata |

As descrições do Jev são ancoradas nos exemplos da tabela SWALIS (`data/referencias/swalis.csv`),
não nos textos do dataset.

## SW-01 · Eixo de progressão (maior nível entre)

| Nível | Pontos |
|---|---|
| 3 | CID de obstrução/instabilidade (K40.0, K40.3, K42.0, K43.0, N13.2, I20.0); `obstrucao`, `risco_vida`, `perda_funcao` |
| 2 | CID C* (exceto C44); biópsia positiva; `cancer_confirmado` |
| 1 | Lesão incerta (D37–D48, R91); C44; `suspeita_malignidade`; **piora na espera** (PS, internação, imagem com progressão ou consulta com piora, depois da entrada na fila; D-97) |
| 0 | nenhum ponto |

C44 (pele não melanoma) fica em 1 mesmo com biópsia ou texto de câncer: confirmam o próprio C44.

## SW-02 · Eixo de sintoma (maior nível entre)

| Nível | Pontos |
|---|---|
| 2 | Dor 7–10; limitação grave; CID com complicação (I83.2, K80.0); `dor_intensa`, `sintoma_grave` |
| 1 | Dor 4–6; limitação moderada; dor **ou** limitação vazia (nunca rebaixar por falta de dado); `sintoma_moderado` |
| 0 | Dor 0–3 e limitação nenhuma/leve |

## SW-03 · Tabela

| Progressão | Classe |
|---|---|
| 3 | A1 |
| 2 | A2 |
| 1 | B |
| 0 | sintoma 0 → D · 1 → C · 2 → B |

## SW-04 · Negação

Termo precedido de "sem", "nega", "nunca", "ausência de", "não há", "não houve" ou "descarta" **na mesma
oração** é ignorado. A oração termina em `. ; : , ! ?` ou em "mas", "porém", "entretanto", "contudo",
"evoluiu": "Sem melhora, evoluiu com suboclusão" mantém a suboclusão. Vale para a palavra-chave e
também para as frases apontadas pelo Jev. Testado nas 10 hérnias K40.9 com "Sem sinais de encarceramento".

## Jev 1.14

- `typesafe/jev-1.14` (OpenRouter) é um modelo de **decisões**: não escreve texto e não funciona em
  `/chat/completions`. Usa `POST https://openrouter.ai/api/alpha/decisions` com `{model, state, questions}`;
  cada frase vira uma pergunta `choice` entre os 8 pontos e `nenhum`, e volta com `probabilities`.
- Configuração: `OPENROUTER_API_KEY` no `.env` da raiz (chave de **API**; chave de gerenciamento dá 401);
  `HP_LLM_MODEL`, `HP_LLM_ENABLED`, `HP_LLM_CACHE`.
- Cache: `data/processed/cache_llm.json` (chave = modelo + `VERSAO_PROMPT` + texto). Mudou as perguntas?
  Troque `VERSAO_PROMPT` e rode `cd backend && python -m app.cli extrair-sinais` (887 textos, ~40 s, centavos).
- A geração da fila lê **só o cache**: saída reproduzível, sem rede. Falha do modelo cai para palavra-chave.

## Score

`score = % do prazo × fator de comorbidade × fator de idade/IRR` (D-103, `domain/fatores.py`). O % do
prazo é `100 × dias na fila / prazo da classe`. Cada fator vai de 1,00 a 1,15 e só desempata dentro da
urgência: com o mesmo tempo de espera, nenhum fator inverte classes vizinhas (1,15² < 21/15). A classe
não muda. Justificativa de cada valor: `docs/score-e-literatura.md`.

## Resultados (2026-10-24)

**Dataset da entrega** (941 solicitações):

| | A1 | A2 | B | C | D |
|---|---|---|---|---|---|
| Só regras (campos + palavra-chave) | 84 | 168 | 199 | 250 | 240 |
| Regras + pontos do Jev | 103 | 166 | 222 | 328 | 122 |
| + piora na espera (D-97) | 103 | 166 | 260 | 300 | 112 |

As classes só sobem com o Jev, nunca descem (nenhuma desceu; conferido nas 941). 272 solicitações têm ponto a
revisar. Verificador oficial OK. Exemplos de subida para A1: SOL-2026-00773 (lesões coronárias >70% em
3 vasos, D→A1), SOL-2024-00181 (hérnia irredutível, D→A1), SOL-2026-00250 (câncer com lesão
subestenosante, A2→A1). Discutível: SOL-2025-00283 ("HB 7,8" em hemorroidas → risco_vida).

**Robustez a texto reescrito** (36 frases fora dos templates do dataset; sinônimos, abreviações, leigo):

| | Detecta o achado | Classe certa |
|---|---|---|
| Só palavra-chave | 1/24 (4%) | 9/36 (25%) |
| Palavra-chave + Jev | 21/24 (88%) | 33/36 (92%) |

As regras de palavra-chave estão ajustadas aos textos sintéticos (a lista veio do verificador, escrita
para os templates); o Jev é o que generaliza. Erros do Jev: "recebeu 2 bolsas de sangue", "emagreceu 12 kg",
"dificuldade para engolir". Ressalvas: amostra pequena, frases e gabarito escritos pelo agente, sem
validação clínica.

## Questões abertas

| ID | Questão | Provisório |
|---|---|---|
| Q-SW1 | "Suspeita de malignidade" conta como progressão 1 ou 2? | 1 (igual a lesão incerta) |
| Q-SW2 | Eventos na espera (PS, internação, progressão em imagem) devem subir o eixo de progressão? | **sobem a nível 1 (B), nunca além** (D-97): destrava a cena da demo; 38 solicitações de C/D para B |
| Q-SW3 | Separação dos termos de palavra-chave por ponto (`TERMOS`) | ver `domain/swalis.py` |
| Q-SW4 | A camada (`urgencia.py`) não usa os pontos do Jev: um A1 por "hérnia irredutível" pode ficar na camada 3 (ex.: SOL-2024-00181, posição 385). A camada 2 deve incluir progressão 3 do SWALIS? | não (cabe à US-08) |
| Q-SW5 | Limiares de confiança do Jev (conta ≥ 0,7; revisar ≥ 0,4) | provisórios |

## Eventos sem relação com a cirurgia (D-123)

PS e internação durante a espera contam como piora (camada 2 e "piora na espera" do SWALIS), **exceto**
quando o Jev responde que o atendimento **não tem relação** com a doença da cirurgia com p ≥ 0,9
(`SwalisRegras.anotar_eventos`, cache `evento-v1-decisoes`). Pergunta: "o atendimento é piora ou complicação
da doença que motivou a cirurgia?" (`relacionado` / `nao_relacionado` / `incerto`). Sem cache ou abaixo de
0,9, o evento continua contando. No dataset: só os 8 "PS por hiperglicemia" saem (p ≥ 0,99).

Efeito com a negação na camada 2 (D-122), fila sem banco: camada 2 206 → 190; mediana dos oncológicos
257 → 248; oncológicos no 1º terço 73% → 76%; "PS/internação recente na 1ª metade" do verificador
100% → 92% (o verificador conta qualquer PS, inclusive os sem relação).
