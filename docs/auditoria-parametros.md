# Auditoria dos parâmetros do score (issue #45)

> **Status:** 24/10/2026 · auditoria sobre a `main` em `cd0802e`. Nenhum valor de código foi alterado.
> **Pergunta da issue:** por que cada parâmetro resolve o problema da fila, e o que a literatura diz dele.
> **Versão para o pitch** (fórmula do score, classificação SWALIS e literatura em linguagem direta): [`score-e-literatura.md`](score-e-literatura.md).

Como ler: cada linha diz o valor, onde ele está, o que faz, por que ajuda a fila e de onde vem.
**Status** usa três rótulos:

- **com fonte**: o valor (ou a regra) bate com uma fonte conferida, da literatura ou do próprio desafio;
- **sem fonte**: escolha do time, sem referência conferida. Fica na lista de pendências (§7);
- **divergente**: existe fonte conferida e o valor do código é diferente dela (§8).

"Desafio" é fonte oficial da hackatona (`data/referencias/swalis.csv`, `src/verificar_fila_priorizada.py`,
`docs/dicionario_dados.md`): não é literatura, mas é a regra contra a qual a banca avalia.
As referências [R1]..[R14] estão no §9 e foram todas conferidas nesta auditoria; o §9 diz o que foi lido em cada uma
(texto completo, resumo ou fonte secundária).

---

## 1. Como os parâmetros se encaixam

```
classe (A1..D)  ←  eixo de progressão (0..3) × eixo de sintoma (0..2)     SW-01..03, [R1]
prazo           ←  tabela da classe (15/21/60/180/360 dias)              desafio
score           =  % do prazo = dias em fila / prazo × 100              ≡ P(t) do SWALIS [R1]
camada (1/2/3)  ←  CID C* (1) · sinal clínico de urgência (2) · demais   regra de ouro I-01
ordem           =  camada ↑, score ↓, entrada mais antiga, id            D-25
```

Os três problemas da fila que os parâmetros atacam:

1. **Regra de ouro (I-01):** oncológico nunca abaixo de paciente sem urgência. Resolvida por
   estrutura (camadas), não por peso: nenhum parâmetro numérico consegue quebrá-la.
2. **Envelhecimento:** o % do prazo cresce todo dia, então quem espera sobe sozinho, e cada classe
   sobe na velocidade do seu prazo (uma A2 sobe ~17× mais rápido que uma D).
3. **Equidade:** pacientes com a mesma necessidade são comparados pela mesma régua (% do prazo,
   desempate pela entrada mais antiga). Classe vem de critérios explícitos e citados, não da
   prioridade manual (89,6% nunca revisada).

---

## 2. Classe e prazo (SWALIS)

| Parâmetro | Valor | Onde | O que faz | Justificativa | Fonte | Status |
|---|---|---|---|---|---|---|
| Dois eixos: progressão × sintoma | progressão 0–3, sintoma 0–2 | `backend/app/domain/swalis.py:144`, `:167` | A classe sai de dois critérios separados | O SWALIS original classifica por dois critérios: presença de progressão rápida da doença e grau de dor, disfunção ou incapacidade | [R1] (método, classificação de urgência) | com fonte |
| Tabela de cruzamento (SW-03) | prog 3→A1, 2→A2, 1→B; prog 0: sint 2→B, 1→C, 0→D | `swalis.py:191-197` | Converte os eixos em classe | [R1]: A1 progressão evidente que piora com a espera; A2 progressão potencial; B dor/disfunção importante sem progressão rápida; C leve; D nenhuma. Bate com prog 3/2 e com sint 2/1/0 | [R1]; descrições de `swalis.csv` (desafio) | com fonte (exceto prog 1, abaixo) |
| Progressão nível 1 → B | lesão incerta, C44, suspeita de malignidade | `swalis.py:192`, `:158`, `:38` | Suspeita de câncer vai para B mesmo sem sintoma | Não há nível intermediário de progressão no SWALIS; o time pôs "suspeita" junto da lesão incerta (Q-SW1) | — | **sem fonte** |
| Prazo A1 | 15 dias | `backend/app/domain/enums.py:22`; `data/referencias/swalis.csv` | Denominador do % do prazo | Tabela do desafio | desafio; [R1] usa **8 dias** | **divergente** |
| Prazo A2 | 21 dias | `enums.py:23` | idem | Tabela do desafio | desafio; [R1] usa **30 dias** | **divergente** |
| Prazo B | 60 dias | `enums.py:24` | idem | Tabela do desafio | desafio; [R1] 60 dias | com fonte |
| Prazo C | 180 dias | `enums.py:25` | idem | Tabela do desafio | desafio; [R1] 180 dias | com fonte |
| Prazo D | 360 dias | `enums.py:26` | idem | Tabela do desafio | desafio; [R1] 360 dias | com fonte |
| Score = % do prazo | `100 × dias / prazo` | `backend/app/infrastructure/swalis_regras.py:56` | Ordena dentro da camada; cresce sozinho todo dia | [R1] define a prioridade como P(t) = (t − t0) × γ, com γ = prazo da classe D / prazo da classe. Com D = 360, P(t) = 3,6 × % do prazo: **a ordem é idêntica**. Pacientes de classes diferentes se encontram quando atingem o mesmo % do prazo | [R1] | com fonte |
| Data de referência | 2026-10-23 | `backend/app/config.py:47` | "Hoje" do cálculo de dias | Data fixa do dataset; nunca `today()` | desafio | com fonte |
| CID de progressão 3 | K40.0, K40.3, K42.0, K43.0, N13.2, I20.0 | `swalis.py:27` | Hérnia com obstrução, hidronefrose obstrutiva e angina instável → A1 | Lista `CID_URGENTE` do verificador; descrições conferidas na CID-10 do DATASUS (obstrução / angina instável). "Angina instável" e "obstrução com risco de estrangulamento" são exemplos de A1 em `swalis.csv` | desafio; CID-10 DATASUS | com fonte |
| CID de sintoma 2 | I83.2, K80.0 | `swalis.py:28` | Varizes com úlcera e colelitíase com colecistite aguda → B | Mesma lista do verificador; a divisão entre os eixos é do time (D-44). `swalis.csv` cita "colelitíase com colecistites de repetição" como exemplo de B | desafio (lista); divisão: time | com fonte (lista) / sem fonte (divisão) |
| Câncer pelo CID → progressão 2 | CID C* exceto C44 | `swalis.py:153-154` | Câncer confirmado → A2 | `swalis.csv`: "neoplasia maligna confirmada e estável" é exemplo de A2 | desafio | com fonte |
| C44 → progressão 1 (B) | C44 | `swalis.py:147-152`, `:161` | Carcinoma de pele não melanoma fica em B mesmo com biópsia | `swalis.csv`: "CBC de pele" é exemplo de B | desafio | com fonte |
| Biópsia positiva → progressão 2 | qualquer data | `swalis.py:156`; `urgencia.py:69` | Câncer escondido (CID não C) sobe para A2 | `swalis.csv`: "biópsia positiva aguardando cirurgia" é exemplo de A2 | desafio | com fonte |
| Lesão incerta → progressão 1 | D37–D48, R91 | `backend/app/domain/cid.py:22-27` | Neoplasia de comportamento incerto / achado de imagem do pulmão → B | Faixa D37–D48 é o grupo "comportamento incerto ou desconhecido" e R91 é "achados anormais de imagem do pulmão" na CID-10 do DATASUS. O nível (1 → B) é do time | CID-10 DATASUS (faixa); nível: time | sem fonte (nível) |
| Corte de dor intensa | EVA ≥ 7 → sintoma 2 | `swalis.py:172` | Dor intensa → B | [R3] (EVA, dor musculoesquelética crônica): ≤ 3,4 interferência leve; 3,5–6,4 moderada; ≥ 6,5 grave. Em EVA inteira, isso é 0–3 / 4–6 / 7–10, exatamente os cortes do código | [R3] | com fonte (ressalva abaixo) |
| Corte de dor moderada | EVA 4–6 → sintoma 1 | `swalis.py:174` | Dor moderada → C | idem | [R3] | com fonte |
| Dor "sem urgência" | EVA ≤ 3 | `metricas.py:24`; `urgencia.py:101`; verificador | Define "sem urgência" e "sintoma" | Definição do verificador oficial; coincide com o corte leve de [R3] | desafio; [R3] | com fonte |
| Limitação funcional | grave → 2; moderada → 1; nenhuma/leve → 0 | `swalis.py:176-179` | Disfunção entra no eixo de sintoma | [R1] usa "dor, disfunção ou incapacidade" no mesmo critério; o verificador trata nenhuma/leve como sem urgência | [R1]; desafio | com fonte |
| Dor ou limitação vazia → sintoma 1 | 1 | `swalis.py:183-186` | Falta de dado não rebaixa para D | Precaução: silêncio não é estabilidade (I-08) | — | **sem fonte** |
| Termos de palavra-chave por ponto | listas `TERMOS` | `swalis.py:64-78` | Texto → ponto de progressão/sintoma | Termos vêm do verificador (`KW_ALARME`); a separação por ponto é do time (D-44, Q-SW3) | desafio (termos); separação: time | sem fonte (separação) |
| Nível de cada ponto | `NIVEL_DO_PONTO` | `swalis.py:50-59` | Ex.: obstrução/risco de vida/perda de função → prog 3 | Ancorado nas descrições de A1/A2/B/C de `swalis.csv` e [R1] (risco de vida ou de perda de órgão/função = A1) | desafio; [R1] | com fonte |
| Negação | gatilhos `sem`, `nega`, `ausência de`, `não há`, `descarta`… com escopo até o fim da oração | `backend/app/domain/texto.py:12-15` | "Sem sinais de encarceramento" não conta | Mesma ideia do NegEx [R8] (gatilho antes do achado + escopo limitado). O NegEx limita o escopo a até 6 palavras; o código usa a oração inteira, cortada por pontuação e adversativas (D-45) | [R8] (adaptado) | **divergente** (escopo) |
| Confiança do Jev que conta | p ≥ 0,7 | `swalis.py:46` | Ponto do LLM muda a classe | Provisório (D-63, Q-SW5) | — | **sem fonte** |
| Confiança do Jev para revisar | 0,4 ≤ p < 0,7 | `swalis.py:47`; `llm_openrouter.py:27` (`PROB_MINIMA`) | Ponto vai ao regulador sem mudar a classe | Provisório (Q-SW5) | — | **sem fonte** |
| Eixo = maior nível entre os pontos | `max` | `swalis.py:133-137` | O Jev só sobe a classe, nunca baixa | Segurança: o LLM não rebaixa (I-05) | — | sem fonte (regra de segurança do time) |

**Ressalva sobre [R3]:** os autores dizem que classificar a EVA em leve/moderada/grave na prática
clínica "parece duvidoso", por causa da correlação baixa a moderada com a função. A amostra é de dor
musculoesquelética crônica, não de fila cirúrgica. Os cortes por descritor verbal no mesmo estudo são
outros (≤ 3,4 / 3,5–7,4 / ≥ 7,5).

---

## 3. Camada, ordem e eventos (trava da regra de ouro)

| Parâmetro | Valor | Onde | O que faz | Justificativa | Fonte | Status |
|---|---|---|---|---|---|---|
| Camada 1 = CID C* | prefixo `C` após normalizar | `cid.py:17-19`; `ranking.py:22`; `montar_fila.py:100` | Todo oncológico acima de todos os outros | Regra de ouro (I-01, I-09): pelo CID, nunca pela flag. Camadas em vez de peso (D-06) | desafio (enunciado e verificador) | com fonte |
| Camada 2 = sinal clínico | CID de complicação, evento de piora na espera, biópsia positiva, alarme no texto | `urgencia.py:77-92` | Urgentes não oncológicos acima dos demais | Os sinais são os do "sem urgência" do verificador; dor e limitação ficam de fora (D-27) | desafio; D-27 | com fonte (sinais) / sem fonte (exclusão de dor, D-27) |
| `CID_URGENTE` | I20.0, K40.3, K40.0, K42.0, K43.0, K80.0, N13.2, I83.2 | `cid.py:5-7` | Define camada 2 | Cópia exata do verificador | desafio | com fonte |
| `_KW_ALARME` | 33 termos | `urgencia.py:19-26` | Alarme no texto → camada 2 | Cópia exata do verificador | desafio | com fonte |
| `EVENTOS_DE_PIORA` | PS, internação, biópsia positiva, imagem com progressão, reavaliação com piora | `urgencia.py:28-34` | Piora na espera → camada 2 | Lista do verificador; só conta durante a espera e sem duplicado (D-23, D-30, D-31) | desafio | com fonte |
| Piora pela flag PRE-06 | + `contato_telefonico/relata_piora` | `preprocessing/flags.py:20-25` | Recalcula `piora_recalculada` | Gatilho `relata_piora` do C-03 (D-28) | — | sem fonte |
| Chave de ordenação | camada ↑, score ↓, entrada ↑, id ↑ | `ranking.py:44-52` | Ordem determinística | [R1]: dentro da mesma classe, quem esperou mais é atendido antes. Entrada mais antiga como desempate segue o mesmo princípio (D-25) | [R1]; D-25 | com fonte |
| Override do score | `score_medico` substitui `score_sistema` | `montar_fila.py:88` | Edição manual do regulador | D-03 / C-10 dizem que "score editado continua envelhecendo". Na `main` o `score_medico` é um número fixo e **não envelhece** | D-03 | **divergente** de decisão do time (ver §8, X-04) |
| Janela de PS recente | 180 dias | `backend/app/domain/metricas.py:13` | Só no indicador "PS recente na 1ª metade" (antes × depois); não entra no score | Igual ao verificador oficial (`REF − 180 dias`), para os números do pitch baterem (D-59) | desafio | com fonte |
| Fila "antes" | alta → média → baixa → vazia, entrada, id | `metricas.py:14`, `:38-42` | Só para a comparação antes × depois | Reproduz a regra atual (D-60) | desafio (`fluxo-sistema.md` §1) | com fonte |

---

## 4. Inbox, recontato e aprendizado

| Parâmetro | Valor | Onde | O que faz | Justificativa | Fonte | Status |
|---|---|---|---|---|---|---|
| `DISTANCIA_MINIMA_NAO_CONFIRMADO` | 2 níveis | `backend/app/domain/inbox.py:12` | Nunca confirmado só vai ao inbox se SWALIS e prioridade divergirem ≥ 2 classes | Inbox nasce com os 296 mais discrepantes, não com 941 (D-64) | — | **sem fonte** |
| Classe implícita da prioridade | alta→B, média→C, baixa/vazia→D | `inbox.py:14-19`; `swalis_stub.py:15` | Referência de comparação do inbox | Mapeamento do time (D-64) | — | **sem fonte** |
| Ordem do inbox | classe mais grave → maior divergência → posição | `inbox.py:42-44` | Regulador vê primeiro quem sobe para A1/A2 | D-67 | — | sem fonte (regra de UX) |
| N do recontato (Q-04) | proposta: 180 dias ou estouro do prazo | `docs/fluxo-sistema.md` C-04 e Q-04; **não implementado** (US-17) | Evita confundir silêncio com estabilidade (I-08) | O C-04 diz "NHS revisa a cada 6 meses". O toolkit do NHS England [R2] pede contato na semana 12, 26 e 52 e, depois de 52 semanas, **pelo menos a cada 12 semanas** | [R2] | **divergente** |
| Limiares do aprendizado (Q-05) | ≥ 5 casos, ≥ 3 reguladores, 90 dias, ≥ 80% | `docs/fluxo-sistema.md` C-14; **não implementado** (US-19) | Filtra propostas de regra | Inspirado no "estilo Waze" | — | **sem fonte** |

---

## 5. Alertas e pendências (não entram no score)

Regra 7 do `AGENTS.md`: HbA1c, ASA, distância, faltas e contagem de eventos não ordenam a fila.
Estes parâmetros só geram alerta ou pendência.

| Parâmetro | Valor | Onde | O que faz | Justificativa | Fonte | Status |
|---|---|---|---|---|---|---|
| `HBA1C_DIABETES` | 6,5% | `preprocessing/inconsistencias.py:38` | PRE-13: diabetes fora do cadastro | Critério diagnóstico de diabetes por A1C ≥ 6,5%, adotado pela ADA em 2010 [R4] | [R4] | com fonte |
| `MIN_TENTATIVAS_SEM_RESPOSTA` | 2 | `inconsistencias.py:37` | PRE-10: contato perdido | Reproduz os 39 casos do `fluxo-sistema.md` (D-47) | — | **sem fonte** |
| `MAX_CARACTERES_GENERICA` | 60 | `inconsistencias.py:39` | PRE-14: justificativa sem conteúdo | 50 casos; com 50 caracteres seriam 45 (D-49) | — | **sem fonte** |

---

## 6. Fatores de comorbidade e mortalidade

Os multiplicadores de `score/` **entram no score da fila** desde a D-103 (`backend/app/domain/fatores.py`,
com as correções X-09, X-10 e X-11). `src/score_mortalidade.py` (Elixhauser, sobrevida em 10 anos)
continua só informativo.

| Parâmetro | Valor | Onde | O que faz | Justificativa | Fonte | Status |
|---|---|---|---|---|---|---|
| Pesos Charlson | IAM 1, ICC 1, DPOC 1, DM sem complicação 1, renal 2, tumor 2, linfoma/leucemia 2, metástase 6 | `src/score_mortalidade.py:105-114`; `score/apply_comorbidity_multiplier.py:27-36` | Índice de comorbidade | Pesos publicados | [R5] (conferido em fonte secundária) | com fonte |
| Pontos de idade do Charlson | <50: 0; 50–59: 1; 60–69: 2; 70–79: 3; 80+: 4 | `score_mortalidade.py:117-127` | Charlson ajustado por idade | O índice combinado idade + comorbidade é de [R6] (1 ponto ≈ 1 década). O código atribui a [R5] (1987) | [R6] | **divergente** (só a atribuição) |
| Sobrevida em 10 anos | `0,983 ^ e^(0,9 × CCI)` | `score_mortalidade.py:163` | Probabilidade informativa | Fórmula atribuída a [R5] | [R5] (fonte secundária) | com fonte |
| Pesos van Walraven | ICC 7, arritmia 5, pulmonar 3, renal 5, DM 0, HAS 0, obesidade −4, hipotireoidismo 0, depressão −3, tumor 4, linfoma 9, metástase 12 | `score_mortalidade.py:90-103` | Elixhauser ponderado | Pesos publicados | [R7] (conferido em fonte secundária) | com fonte |
| Leucemia com peso de linfoma | C91–C95 → `linfoma_leucemia` = 9 | `score_mortalidade.py:53`, `:101` | Soma 9 pontos para leucemia | O Elixhauser na versão de [R9] tem 31 categorias, com "linfoma" e sem nenhuma de leucemia; logo não existe peso van Walraven para leucemia | [R7], [R9] | **divergente** |
| `cardiopatia isquemica` e I25 → infarto | 1 ponto | `apply_comorbidity_multiplier.py:42`, `:78`; `score_mortalidade.py:72` | Conta como IAM | A categoria do Charlson é infarto do miocárdio; I25 é "doença isquêmica crônica do coração" (CID-10 DATASUS), mais ampla | [R5]; CID-10 DATASUS | **divergente** |
| E10–E14 → DM sem complicação | 1 ponto | `apply_comorbidity_multiplier.py:84` | Todo diabetes vale 1 | O Charlson dá 2 pontos para diabetes com lesão de órgão-alvo; [R9] separa "diabetes sem complicação" de "diabetes com complicação" | [R5] (fonte secundária), [R9] | **divergente** (subestima) |
| Faixas Charlson → multiplicador | 0→1,00; 1→1,03; 2→1,06; 3–4→1,10; 5+→1,15 | `apply_comorbidity_multiplier.py:112-120` | Fator contextual | Regra de produto (`score/decisoes.md` D-18) | — | **sem fonte** |
| Fator idade/mortalidade | `1 + 0,075 × min(log2(IRR), 2)`, teto 1,15 | `apply_idade_mortality_multiplier.py:81-82` | Fator contextual | Regra de produto (`score/decisoes.md` D-12) | — | **sem fonte** |
| Faixas etárias do IRR | 0–17, 18–39, 40–49, 50–59, 60–69, 70–79, 80+ | `apply_idade_mortality_multiplier.py:49-60` | Célula da tabela SIM/IBGE | "Faixas amplas e interpretáveis" (`score/decisoes.md` D-07) | — | **sem fonte** |
| Sem limiar mínimo de óbitos | 0 | `score/decisoes.md` D-09 | Toda célula tem IRR, mesmo instável | Retornar valor para todos | [R12]: o NCHS não publica taxa com menos de 20 óbitos (erro padrão relativo ≥ 23%) | **divergente** (107 de 357 células; 26 pacientes com fator > 1 vindo delas) |
| Charlson sem idade | idade fora do índice de comorbidade | `score/decisoes.md` D-14 | Evita contar a idade no Charlson e no IRR | 1 ponto de comorbidade ≈ 1 década de idade no índice combinado | [R6] | com fonte |
| CID principal fora do Charlson | — | `score/decisoes.md` D-15 | Não conta a doença da cirurgia como comorbidade | O Elixhauser separa comorbidades do motivo principal da internação | [R10] | com fonte |
| Hierarquia do Charlson | não aplicada (tumor + metástase somariam 8) | `apply_comorbidity_multiplier.py:139` | Soma todas as categorias achadas | Metástase substitui malignidade; diabetes com complicação substitui sem complicação | [R11] | **divergente** (0 casos no dataset) |

A origem da tabela IRR (SIM 2019–2023 e projeções IBGE revisão 2024) **não foi conferida** nesta
auditoria: o arquivo `score/references/irr_nacional_cid_idade_2019_2023.parquet` não traz o script que o
gerou. O `src/score_mortalidade.py` também cita Quan et al. (2005) para os códigos oncológicos: a citação e as
categorias foram conferidas ([R9]), mas a **lista de códigos CID-10** de cada categoria não (o texto
completo não foi lido). Por isso X-07 fala da categoria (infarto), não do código exato.

**Fora do escopo** (não mexem em score, classe ou ordem): `MAX_MOTIVOS = 3` (`explicacao.py:5`, só
o texto da explicação) e `page_size ≤ 200` (`api/routers/fila.py:24`, paginação).

---

## 7. Pendências: parâmetros sem fonte

Precisam de validação com os mentores (HSL) ou ficam declarados como escolha do time (D-81).

| # | Parâmetro | Valor | Pergunta para os mentores |
|---|---|---|---|
| P-01 | Progressão 1 → B (suspeita de malignidade, lesão incerta) | B | Suspeita não confirmada deve ser B ou A2? (Q-SW1) |
| P-02 | Dor/limitação vazia → sintoma 1 | C no mínimo | Falta de dado deve impedir D? |
| P-03 | Separação dos termos por ponto | `TERMOS` | Quais termos são risco de vida e quais são suspeita? (Q-SW3) |
| P-04 | Divisão I83.2/K80.0 no eixo de sintoma | sintoma 2 | Colecistite aguda é progressão (A1/A2) ou sintoma (B)? |
| P-05 | Confiança do Jev | 0,7 / 0,4 | Calibrar com um gabarito clínico (Q-SW5) |
| P-06 | Dor e limitação fora da camada 2 | D-27 | Sintoma intenso sem sinal clínico pode ficar na camada 3? |
| P-07 | Piora por `relata_piora` | PRE-06 | Relato telefônico de piora conta como piora? |
| P-08 | Distância mínima do inbox | 2 | 2 níveis é o corte certo para a carga inicial? |
| P-09 | Classe implícita da prioridade | alta→B… | Prioridade "alta" equivale a B? |
| P-10 | Limiares do aprendizado | 5 / 3 / 90 d / 80% | (Q-05) |
| P-11 | Tentativas para contato perdido | 2 | |
| P-12 | Corte de justificativa genérica | 60 caracteres | |
| P-13 | Fatores de comorbidade e idade | 1,00–1,15 | Só valem se o time decidir ligá-los ao score (hoje não estão) |
| P-14 | Faixas etárias e ausência de limiar de óbitos do IRR | — | idem |

## 8. Divergências da literatura ou de decisões

| # | O quê | Código | Fonte | Impacto | Sugestão (não aplicada) |
|---|---|---|---|---|---|
| X-01 | Prazos A1 e A2 | 15 e 21 dias | [R1]: 8 e 30 dias | O desafio adaptou a tabela; B/C/D batem. Com 15/21, A1 envelhece mais devagar e A2 mais rápido do que no SWALIS original | Manter a tabela do desafio (é a que a banca usa) e dizer no pitch que é adaptada do SWALIS (registrado em D-80) |
| X-02 | N do recontato (Q-04) e texto do C-04 | proposta 180 dias; "NHS revisa a cada 6 meses" | [R2]: contato na semana 12, 26, 52 e depois a cada 12 semanas | Com 180 dias, o primeiro recontato vem depois do que o NHS recomenda; a frase do C-04 não bate com [R2] | Na US-17, considerar o calendário 12/26/52 semanas e corrigir a frase do C-04 |
| X-03 | Escopo da negação | oração inteira | [R8]: até 6 palavras após o gatilho | Escopo maior nega mais termos; o time cortou por pontuação e adversativas para não apagar urgência (D-45) | Manter; citar como "adaptado do NegEx" |
| X-04 | `score_medico` não envelhece | `montar_fila.py:88` usa o valor fixo | D-03 / C-10: "score editado continua envelhecendo" | Paciente editado fica parado enquanto os outros sobem | Já resolvido na branch `feat/US-13-14-15-decisoes-eventos` (D-71 dela), ainda não mergeada |
| X-05 | Atribuição do ajuste por idade do Charlson | "Charlson et al. 1987" | [R6] (1994) | Só a citação; os pontos estão certos | Corrigir o comentário em `score_mortalidade.py:118` |
| X-06 | Leucemia com peso de linfoma no Elixhauser | 9 pontos | [R9]: o Elixhauser não tem categoria de leucemia | Soma 9 pontos que o índice não prevê | Tirar C91–C95 do `linfoma` no Elixhauser (no Charlson continuam valendo 2, como malignidade) |
| X-07 | I25 / "cardiopatia isquêmica" como infarto | 1 ponto | [R5]: infarto do miocárdio | Superestima (doença isquêmica crônica ≠ infarto) | Mapear só I21/I22/I25.2 ou texto "infarto" |
| X-08 | Todo diabetes como "sem complicação" | 1 ponto | [R5]: com lesão de órgão-alvo = 2 | Subestima (0 casos no dataset hoje) | Ler o 4º caractere do CID (E1x.2–E1x.5) |
| X-09 | IRR sem limiar mínimo de óbitos | `score/decisoes.md` D-09 | [R12]: < 20 óbitos = taxa não confiável | 26 pacientes recebem fator > 1 de células instáveis | **Corrigido na D-103** |
| X-10 | Hierarquia do Charlson não aplicada | tumor + metástase = 8 | [R11]: metástase substitui malignidade (6) | 0 casos no dataset | **Corrigido na D-103** |
| X-11 | Teto `min(100, …)` da composição proposta | `score/README.md` | — (incompatibilidade interna) | O score da fila é % do prazo e passa de 100; o teto empataria todos os atrasados | **Corrigido na D-103** |

Nenhum parâmetro contradiz a regra de ouro (I-01): ela não depende de peso, só da camada 1 pelo CID,
e o verificador oficial continua sendo o portão (I-07). X-04 contraria uma decisão (D-03), não uma
invariante. X-05..X-08 estão em módulos que não ordenam a fila; X-09..X-11 foram corrigidos na D-103.

---

## 9. Referências conferidas

| ID | Referência | O que foi conferido |
|---|---|---|
| R1 | Valente R, Testi A, Tanfani E, Fato M, Porro I, Santo M, Santori G, Torre G, Ansaldo G. *A model to prioritize access to elective surgery on the basis of clinical urgency and waiting time.* BMC Health Services Research. 2009;9:1. doi:[10.1186/1472-6963-9-1](https://doi.org/10.1186/1472-6963-9-1) · [PMC2651867](https://pmc.ncbi.nlm.nih.gov/articles/PMC2651867) | Texto completo: projeto SWALIS; classes A1 8, A2 30, B 60, C 180, D 360 dias; P(t) = (t − t0) × γ, γ = prazo de D / prazo da classe; dois critérios (progressão; dor, disfunção ou incapacidade) |
| R2 | NHS England. *Validation toolkit and guidance.* Version 1, 1 December 2022. Publication reference PR2121_ii. [PDF](https://www.england.nhs.uk/wp-content/uploads/2022/12/B2121ii-validation-toolkit-and-guidance-december-2022.pdf) | Figura 2: contato na semana 12, 26 e 52; depois de 52 semanas, validação a cada 12 semanas no mínimo; validação técnica, administrativa e clínica |
| R3 | Boonstra AM, Schiphorst Preuper HR, Balk GA, Stewart RE. *Cut-off points for mild, moderate, and severe pain on the visual analogue scale for pain in patients with chronic musculoskeletal pain.* Pain. 2014;155(12):2545–2550. doi:[10.1016/j.pain.2014.09.014](https://doi.org/10.1016/j.pain.2014.09.014) | Resumo: cortes por interferência na função ≤ 3,4 / 3,5–6,4 / ≥ 6,5; por descritor ≤ 3,4 / 3,5–7,4 / ≥ 7,5; ressalva dos autores. Texto completo não lido |
| R4 | American Diabetes Association. Standards of Medical Care in Diabetes, critério diagnóstico A1C ≥ 6,5% (adotado em 2010). [Notícia da adoção](https://mdedge.com/content/ada-officially-endorses-hba1c-diagnosis-diabetes) | Corte de 6,5%. Não conferimos a edição de 2026 |
| R5 | Charlson ME, Pompei P, Ales KL, MacKenzie CR. *A new method of classifying prognostic comorbidity in longitudinal studies: development and validation.* J Chronic Dis. 1987;40(5):373–383. doi:[10.1016/0021-9681(87)90171-8](https://doi.org/10.1016/0021-9681(87)90171-8) · [PubMed 3558716](https://pubmed.ncbi.nlm.nih.gov/3558716/) | Citação e resumo. Pesos, pontos de idade e fórmula de sobrevida conferidos em fonte secundária ([calculadora Omni](https://wba.omnicalculator.com/health/cci), que cita este artigo) |
| R6 | Charlson M, Szatrowski TP, Peterson J, Gold J. *Validation of a combined comorbidity index.* J Clin Epidemiol. 1994;47(11):1245–1251. doi:[10.1016/0895-4356(94)90129-5](https://doi.org/10.1016/0895-4356(94)90129-5) | Resumo: índice combinado idade + comorbidade; 1 ponto ≈ 1 década de idade |
| R7 | van Walraven C, Austin PC, Jennings A, Quan H, Forster AJ. *A modification of the Elixhauser comorbidity measures into a point system for hospital death using administrative data.* Med Care. 2009;47(6):626–633 | Citação. Pesos conferidos em fonte secundária: tabela de pesos van Walraven em [PMC7651966](https://pmc.ncbi.nlm.nih.gov/articles/PMC7651966) |
| R8 | Chapman WW, Bridewell W, Hanbury P, Cooper GF, Buchanan BG. *A simple algorithm for identifying negated findings and diseases in discharge summaries.* J Biomed Inform. 2001;34:301–310. [PDF](https://www.dbmi.pitt.edu/wp-content/uploads/2022/10/A-simple-algorithm-for-identifying-negated-findings-and-diseases-in-discharge-summaries.pdf) | Resumo: gatilhos de negação por expressão regular com escopo de 1 a 6 palavras |
| R9 | Quan H, Sundararajan V, Halfon P, Fong A, Burnand B, Luthi JC, Saunders LD, Beck CA, Feasby TE, Ghali WA. *Coding algorithms for defining comorbidities in ICD-9-CM and ICD-10 administrative data.* Med Care. 2005;43(11):1130–1139 | Citação e método (resumo). Categorias Charlson e Elixhauser dessa versão conferidas na documentação do pacote R [`comorbidity`](https://rdrr.io/github/ellessenne/comorbidity/man/comorbidity.html), que implementa Quan 2005: o Elixhauser tem 31 categorias, com "lymphoma" e sem leucemia, e o Charlson separa diabetes com e sem complicação. Lista de códigos CID-10 não conferida |
| R10–R14 | Elixhauser 1998; HDR UK (hierarquia do Charlson); CDC/NCHS (confiabilidade estatística); definição de causa básica do SIM; Western Canada Waiting List Project 2004 | Citação completa e o que foi lido em [`score-e-literatura.md`](score-e-literatura.md#7-referências) §7 |

**Fontes do desafio** (não são literatura): `data/referencias/swalis.csv` (classes, prazos e exemplos),
`src/verificar_fila_priorizada.py` (CID urgente, termos de alarme, eventos de piora, "sem urgência",
janela de 180 dias), `docs/dicionario_dados.md` ("adaptado do modelo SWALIS") e as tabelas CID-10 do
DATASUS em `data/referencias/CID10CSV/`.
