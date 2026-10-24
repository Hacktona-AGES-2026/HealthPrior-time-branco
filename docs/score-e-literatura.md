# Score, classificação SWALIS e base na literatura

> **Para o pitch e para a banca.** Fórmula exata de cada peça, como a classe SWALIS é decidida e qual
> referência sustenta cada escolha. Estado do código: `main` em `cd0802e` (24/10/2026).
> Números: dataset da entrega (941 solicitações), regras + cache do Jev, data de referência 23/10/2026.
> Auditoria parâmetro a parâmetro (arquivo:linha, status): [`auditoria-parametros.md`](auditoria-parametros.md).
> Toda referência [Rn] foi conferida; o §7 diz o que foi lido em cada uma.

## 1. Em uma frase

**A classe diz quanto tempo a doença tolera esperar (SWALIS); o score diz quanto desse tempo já foi
gasto; a camada garante que nenhum câncer fica atrás de quem não tem urgência.**

```
dados do paciente ──► PONTOS com evidência ──► CLASSE SWALIS (A1..D) ──► PRAZO (dias)
                                                                         │
data de entrada ──────────────────────────► DIAS EM FILA ───────────────┤
                                                                         ▼
                                            SCORE = % do prazo consumido
CID C*? sinal clínico de urgência? ──► CAMADA (1, 2, 3)                  │
                                                                         ▼
                              ORDEM = camada ↑ · score ↓ · entrada ↑ · id ↑
```

---

## 2. Classificação SWALIS: como a classe é decidida

### 2.1 De onde vem o método

O SWALIS (*Surgical Waiting List Info System*) é um projeto financiado pelo Ministério da Saúde da Itália
em 2001 e publicado por Valente et al. [R1]. A urgência é avaliada por **dois critérios**: presença de
**progressão rápida** da doença e **grau de dor, disfunção ou incapacidade**. Cada classe tem um tempo
máximo até o tratamento (MTBT). Ferramentas de priorização do Canadá usam os mesmos ingredientes: o
instrumento do *Western Canada Waiting List Project* para quadril e joelho soma critérios de dor, função
e potencial de progressão da doença num escore ponderado [R14].

| Classe | Critério em [R1] | Prazo em [R1] | Prazo no HealthPrior (desafio) |
|---|---|---|---|
| A1 | progressão rápida evidente, a espera piora o desfecho | 8 dias | **15 dias** |
| A2 | progressão potencial | 30 dias | **21 dias** |
| B | dor, disfunção ou incapacidade importantes, sem progressão rápida | 60 dias | 60 dias |
| C | dor ou disfunção leves | 180 dias | 180 dias |
| D | sem dor, disfunção ou incapacidade | 360 dias | 360 dias |

Usamos os prazos da tabela do desafio (`data/referencias/swalis.csv`), que o dicionário de dados chama de
"adaptado do modelo SWALIS". B, C e D são iguais ao artigo; A1 e A2 foram adaptados (D-80).

### 2.2 Etapa 1: pontos, cada um com evidência citada

Cada ponto alimenta um eixo num nível. Ele pode vir de três origens, e a justificativa da fila diz qual:

| Origem | O que lê | Como evita erro |
|---|---|---|
| **Campo / CID** | CID principal, dor EVA, limitação funcional, eventos (biópsia) | Dado estruturado |
| **Palavra-chave** | Justificativa clínica e observações | Termos do verificador oficial; **negação** ("sem sinais de encarceramento" não conta), na linha do NegEx [R8] |
| **Jev (LLM)** | Cada frase do texto: qual dos 8 pontos ela descreve, com probabilidade | Só conta com p ≥ 0,7; 0,4–0,7 vai para o regulador revisar; a citação é a frase literal, conferida no texto e não negada |

| Ponto | Eixo · nível | Exemplos que disparam |
|---|---|---|
| `obstrucao` | progressão 3 | encarceramento, estrangulamento, suboclusão, hérnia irredutível |
| `risco_vida` | progressão 3 | colangite, melena, sepse, transfusão, síncope, angina em repouso |
| `perda_funcao` | progressão 3 | hidronefrose, glaucoma facomórfico, dano neurológico |
| CID de obstrução/instabilidade | progressão 3 | K40.0, K40.3, K42.0, K43.0 (hérnia com obstrução), N13.2, I20.0 (angina instável) |
| câncer pelo CID (C*, exceto C44), biópsia positiva, `cancer_confirmado` | progressão 2 | C18.7 com anatomopatológico |
| lesão incerta (D37–D48, R91), C44, `suspeita_malignidade` | progressão 1 | perda ponderal, disfagia, PSA em elevação |
| dor EVA 7–10, limitação grave, I83.2, K80.0, `dor_intensa`, `sintoma_grave` | sintoma 2 | acamado, úlcera de pressão |
| dor EVA 4–6, limitação moderada, `sintoma_moderado`; dor ou limitação **sem dado** | sintoma 1 | — |
| dor EVA 0–3 e limitação nenhuma/leve | sintoma 0 | — |

**Os cortes de dor têm base:** em pacientes com dor musculoesquelética crônica, EVA ≤ 3,4 corresponde
a interferência leve na função, 3,5–6,4 a moderada e ≥ 6,5 a grave [R3]. Na EVA inteira (0–10), isso
é exatamente 0–3 / 4–6 / 7–10. Os próprios autores avisam que a classificação na prática clínica é
incerta, então tratamos o corte como critério e não como diagnóstico.

### 2.3 Etapa 2: decisão pela tabela (determinística)

```
nivel_progressao = MAIOR nível entre os pontos de progressão   (0 a 3; sem ponto = 0)
nivel_sintoma    = MAIOR nível entre os pontos de sintoma      (0 a 2; sem ponto = 0)

classe = A1  se nivel_progressao = 3
         A2  se nivel_progressao = 2
         B   se nivel_progressao = 1
         B   se nivel_progressao = 0 e nivel_sintoma = 2
         C   se nivel_progressao = 0 e nivel_sintoma = 1
         D   se nivel_progressao = 0 e nivel_sintoma = 0
```

- **Por que o máximo:** um único sinal grave basta (é assim que o SWALIS define A1). Também garante que
  o Jev **só sobe** a classe: sem ele, a classe é a das regras; com ele, igual ou maior.
- **Quem decide é a tabela, não o LLM** (I-05). A classe sai como "sugerida, não confirmada" até o
  regulador (I-04).
- **Exceção C44** (pele não melanoma): fica em B mesmo com biópsia, porque a tabela do desafio usa
  "CBC de pele" como exemplo de B.

**Resultado no dataset:** A1 102 · A2 166 · B 225 · C 326 · D 122. Só com regras (sem Jev) seriam
84 / 168 / 199 / 250 / 240: 150 classes sobem e nenhuma desce (`docs/swalis.md`).

---

## 3. Fórmula exata do score

### 3.1 Score da fila (implementado e usado na ordem)

```
dias_em_fila   = data_referência − data_entrada_fila                 (23/10/2026, nunca "hoje")
classe         = classe_medico, se o regulador editou; senão a classe SWALIS
prazo          = {A1: 15, A2: 21, B: 60, C: 180, D: 360}[classe]
score_sistema  = arredonda(100 × dias_em_fila / prazo, 1 casa)       → "% do prazo consumido"
score_efetivo  = score_medico, se o regulador editou o score; senão score_sistema
```

Código: `backend/app/infrastructure/swalis_regras.py:55-56` e `backend/app/application/montar_fila.py:88-113`.

**É o score do SWALIS publicado.** Em [R1] a prioridade é `P(t) = (t − t0) × γ`, com
`γ = MTBT da classe D / MTBT da classe`. Com D = 360 dias:

```
P(t) = dias_em_fila × 360 / prazo = 3,6 × score_sistema
```

Mesma ordem, só muda a escala. O artigo chama essa unidade de "dias de espera ajustados pela
necessidade". Na prática:

- **Envelhecimento:** o score cresce sozinho todo dia, sem ninguém mexer. Paciente esquecido sobe.
- **Velocidade por urgência:** uma A2 ganha 4,8 pontos por dia (100/21); uma D, 0,28 (100/360). A A2 sobe
  ~17 vezes mais rápido.
- **Equidade entre classes:** 100% significa "estourou o prazo" em qualquer classe. Um paciente D com 400
  dias (111%) passa na frente de um B com 30 dias (50%), porque o D já estourou o que a própria doença
  tolera e o B não.

**Exemplos reais:**

| Solicitação | Classe | Dias | Conta | Score |
|---|---|---|---|---|
| SOL-2023-00010 (adenocarcinoma de sigmoide, C18.7) | A2 (21 d) | 1.318 | 100 × 1.318 / 21 | **6.276,2%** |
| SOL-2026-00637 (colangite há 3 semanas, só no texto) | A1 (15 d) | 101 | 100 × 101 / 15 | **673,3%** |
| SOL-2026-00757 (D37.4 com biópsia positiva) | A2 (21 d) | 72 | 100 × 72 / 21 | **342,9%** |

### 3.2 Camada e ordem final

```
camada = 1  se o CID normalizado começa com "C"                      (regra de ouro, pelo CID, nunca pela flag)
         2  se tem sinal clínico de urgência:
              CID de complicação (I20.0, K40.0, K40.3, K42.0, K43.0, K80.0, N13.2, I83.2)
              ou evento de piora durante a espera (PS, internação, imagem com progressão,
                 reavaliação com piora; sem histórico e sem duplicado)
              ou biópsia positiva
              ou termo de alarme na justificativa
         3  demais

ordem = camada crescente → score_efetivo decrescente → data de entrada mais antiga → solicitacao_id
```

Código: `backend/app/domain/ranking.py:44-52` e `backend/app/domain/urgencia.py:77-92`.

- **Por que camada e não peso:** a regra de ouro é eliminatória. Com camadas, nenhum número consegue
  colocar um câncer atrás de um paciente sem urgência (D-06). Exemplo: um câncer de pele classe B com
  15 dias (25%) ficaria atrás de uma hérnia D com 400 dias (111%) se só o score ordenasse.
- **Desempate pela entrada mais antiga:** em [R1], dentro da mesma classe, quem esperou mais é atendido
  antes.
- **Resultado:** camadas 177 / 206 / 558. O SOL-2023-00010 estava na **posição 606** na fila por prioridade
  manual e agora está na **posição 1**. O verificador oficial passa.

---

## 4. Fatores contextuais: comorbidade e idade/mortalidade

> **Status no código:** os dois fatores são calculados por `score/` e ficam em `data/processed/`, com
> regra e explicação por paciente. **Hoje eles não entram na ordem da fila** (`score/decisoes.md` D-21).
> Ligá-los ao score exige uma decisão do time (ver §4.4).

### 4.1 Multiplicador de comorbidade

```
categorias      = categorias Charlson achadas no texto de comorbidades + CID secundário
                  (sem o CID principal, sem idade; cada categoria conta uma vez)
charlson_sem_idade = Σ peso(categoria)
                  IAM 1 · ICC 1 · doença pulmonar crônica 1 · diabetes 1 · doença renal 2
                  tumor sólido 2 · linfoma/leucemia 2 · metástase 6
mult_comorbidade = 1,00 se Charlson 0 · 1,03 se 1 · 1,06 se 2 · 1,10 se 3–4 · 1,15 se ≥ 5
```

Código: `score/apply_comorbidity_multiplier.py:27-120`. No dataset: Charlson 0 = 511, 1 = 331, 2 = 89,
3 = 7, 4 = 3; multiplicador máximo observado 1,10.

### 4.2 Multiplicador de idade e mortalidade (IRR)

```
cid_3          = CID principal com 3 caracteres (C18.7 → C18)
faixa          = 0–17 · 18–39 · 40–49 · 50–59 · 60–69 · 70–79 · 80+
taxa(cid, f)   = óbitos com causa básica = cid na faixa f / população da faixa f   (SIM 2019–2023 / IBGE)
taxa_media(cid)= óbitos do cid em todas as idades / população total
IRR            = taxa(cid, faixa) / taxa_media(cid)
mult_idade     = 1,00                                    se IRR ausente, 0 ou ≤ 1
                 min(1,15; 1 + 0,075 × min(log2 IRR; 2))  se IRR > 1
```

Código: `score/apply_idade_mortality_multiplier.py:64-82`; tabela em
`score/references/irr_nacional_cid_idade_2019_2023.parquet` (57 CIDs × 7 faixas = 399 células).

Exemplo (tabela do repo): C18 aos 70–79 anos tem taxa de 38,4 por 100 mil contra média de 6,5 do C18 →
IRR 5,92 → log2 = 2,57, limitado a 2 → **mult_idade = 1,15**. No dataset: 460 pacientes com ajuste,
326 neutros por IRR ≤ 1, 155 neutros por IRR indisponível ou célula sem óbito.

### 4.3 Base na literatura de cada decisão do `score/decisoes.md`

| Decisão (score/) | O que a literatura diz | Fonte | Status |
|---|---|---|---|
| D-14/D-18: usar o **Charlson** | Índice prognóstico de mortalidade criado e validado em coortes (mortalidade em 1 ano subiu de 12% com escore 0 para 85% com escore ≥ 5); pesos de 1 a 6 por condição | [R5] | com fonte |
| Pesos usados (1/1/1/1/2/2/2/6) | Batem com os pesos publicados | [R5], [R11] | com fonte |
| D-14: **Charlson sem idade** porque a idade já está no IRR | No índice combinado, 1 ponto de comorbidade equivale a ~1 década de idade: idade e comorbidade são somadas como coisas distintas, então usar as duas vezes duplicaria o efeito | [R6] | com fonte |
| D-15: **não contar o CID principal** como comorbidade | O Elixhauser foi construído para separar comorbidades do motivo principal da internação | [R10] | com fonte |
| D-17: categoria conta uma vez | Regra de hierarquia do Charlson: metástase substitui "malignidade" e diabetes com complicação substitui sem complicação; a condição mais leve não soma | [R11] | **parcial**: conta uma vez, mas não aplica a hierarquia (tumor + metástase somaria 8, não 6). No dataset: **0 casos**, sem impacto hoje |
| D-19: **não usar Elixhauser** como multiplicador | Os pesos de van Walraven foram derivados para **morte hospitalar** e têm valores negativos (obesidade −4, depressão −3) | [R7] | com fonte |
| D-05: usar `CAUSABAS` do SIM | Causa básica é a doença que iniciou a cadeia de eventos que levou à morte, selecionada por regras da OMS/CID-10 | [R13] | com fonte |
| D-03/D-04: **taxa** (óbitos / população), não contagem | Comparar idades exige taxa por população; IRR é uma razão de taxas | definição; sem referência específica conferida | — |
| D-09: **sem limiar mínimo de óbitos** | O NCHS (CDC) não publica taxa específica por idade com **menos de 20 óbitos**: o erro padrão relativo passa de 23% | [R12] | **divergente**: 107 das 357 células com IRR têm < 20 óbitos; **26 pacientes** recebem multiplicador > 1 vindo dessas células |
| D-13/D-20: fator **nunca reduz** (piso 1,00) | Precaução do time: ausência de evidência não é evidência de menor risco (mesma ideia de I-08) | — | sem fonte (regra de produto) |
| D-12/D-18/D-24: **conversão em 1,00–1,15** (log2, 0,075, faixas, tetos) | O próprio `score/decisoes.md` diz que são "regras de produto, não pesos calibrados" | — | sem fonte (declarado) |
| D-07: sete faixas etárias | Escolha de interpretabilidade e volume | — | sem fonte |
| Diabetes do CID secundário sempre "sem complicação" | Charlson dá 2 pontos para diabetes com complicação crônica | [R11] | **divergente**, mas **0 casos** no dataset (nenhum E1x.2–E1x.5) |

### 4.4 Se o time quiser ligar os fatores ao score

O `score/README.md` propõe `score_proposto = min(100, score_base × mult_comorbidade × mult_idade)`,
pensado para um score de 0 a 100. **O score da fila não é 0–100**: é % do prazo, e passa de 100 para
quem estourou o prazo (SOL-2023-00010 tem 6.276%). Aplicado ao % do prazo, o teto de 100 empataria
todos os atrasados e apagaria a ordem entre eles. Se for ligar, é preciso uma decisão nova
(sem o teto, ou multiplicando o prazo), com simulação do impacto e o verificador passando. No dataset
o produto dos dois fatores chega a 1,265, e 27 pacientes ficam acima de 1,2.

---

## 5. O que podemos dizer no pitch

**Pode dizer (com fonte):**

1. "Usamos o SWALIS, modelo italiano publicado [R1]: dois critérios clínicos, progressão e dor/função,
   cada classe com um prazo máximo."
2. "Nosso score é o mesmo do SWALIS: dias esperando ponderados pelo prazo da classe. Todo mundo
   envelhece, e quem tem doença mais urgente envelhece mais rápido."
3. "Os cortes de dor 0–3, 4–6 e 7–10 vêm de estudo de validação da escala visual analógica [R3]."
4. "Ferramentas canadenses de fila cirúrgica usam os mesmos critérios: dor, função e progressão [R14]."
5. "Comorbidade pelo índice de Charlson [R5], sem contar a idade duas vezes [R6] e sem contar a doença
   da cirurgia como comorbidade [R10]. Mortalidade por idade com dados oficiais do SIM e do IBGE."
6. "O LLM não decide: ele aponta a frase, a tabela decide e o regulador confirma."
7. "O NHS recontata quem espera nas semanas 12, 26 e 52 [R2]; nós geramos recontato para quem fica
   em silêncio."

**Não dizer (ou dizer com a ressalva):**

- que os prazos são os do artigo: A1 e A2 foram **adaptados** pelo desafio (8→15 e 30→21 dias);
- que comorbidade e idade já mudam a ordem: **hoje não mudam** (§4);
- que a conversão em 1,03–1,15 vem da literatura: é **regra de produto**;
- que o modelo foi validado clinicamente: os dados são **100% sintéticos**.

---

## 6. Limites conhecidos

- **Q-SW4:** a camada não usa os pontos do Jev. Ex.: SOL-2024-00181 (hérnia irredutível, A1 pelo Jev)
  está na posição 387, camada 3.
- O score editado pelo regulador (`score_medico`) não envelhece na `main`; a correção está na branch
  `feat/US-13-14-15-decisoes-eventos` (ainda não mergeada).
- Parâmetros sem fonte e divergências completas: `auditoria-parametros.md` §7 e §8.

---

## 7. Referências

R1–R9 são as mesmas da [auditoria](auditoria-parametros.md#9-referências-conferidas).

| ID | Referência | O que foi conferido |
|---|---|---|
| R1 | Valente R, Testi A, Tanfani E, et al. *A model to prioritize access to elective surgery on the basis of clinical urgency and waiting time.* BMC Health Serv Res. 2009;9:1. doi:[10.1186/1472-6963-9-1](https://doi.org/10.1186/1472-6963-9-1) | Texto completo ([PMC2651867](https://pmc.ncbi.nlm.nih.gov/articles/PMC2651867)): classes, MTBT, P(t), critérios |
| R2 | NHS England. *Validation toolkit and guidance.* v1, 1 dez. 2022 (PR2121_ii). [PDF](https://www.england.nhs.uk/wp-content/uploads/2022/12/B2121ii-validation-toolkit-and-guidance-december-2022.pdf) | Figura 2: contato nas semanas 12/26/52 e depois a cada 12 semanas |
| R3 | Boonstra AM, Schiphorst Preuper HR, Balk GA, Stewart RE. *Cut-off points for mild, moderate, and severe pain on the visual analogue scale for pain in patients with chronic musculoskeletal pain.* Pain. 2014;155(12):2545–2550. doi:[10.1016/j.pain.2014.09.014](https://doi.org/10.1016/j.pain.2014.09.014) | Resumo: cortes e ressalva dos autores |
| R5 | Charlson ME, Pompei P, Ales KL, MacKenzie CR. J Chronic Dis. 1987;40(5):373–383. [PubMed 3558716](https://pubmed.ncbi.nlm.nih.gov/3558716/) | Resumo (mortalidade em 1 ano 12% → 85%); pesos em fonte secundária |
| R6 | Charlson M, Szatrowski TP, Peterson J, Gold J. *Validation of a combined comorbidity index.* J Clin Epidemiol. 1994;47(11):1245–1251 | Resumo: 1 ponto ≈ 1 década de idade |
| R7 | van Walraven C, Austin PC, Jennings A, Quan H, Forster AJ. Med Care. 2009;47(6):626–633 | Citação; pesos em fonte secundária ([PMC7651966](https://pmc.ncbi.nlm.nih.gov/articles/PMC7651966)) |
| R8 | Chapman WW, Bridewell W, Hanbury P, Cooper GF, Buchanan BG. J Biomed Inform. 2001;34:301–310 | Resumo: NegEx |
| R10 | Elixhauser A, Steiner C, Harris DR, Coffey RM. *Comorbidity measures for use with administrative data.* Med Care. 1998;36(1):8–27. [PubMed 9431328](https://pubmed.ncbi.nlm.nih.gov/9431328/) | Resumo: 30 medidas; comorbidades separadas do motivo principal da internação. Regras detalhadas de exclusão não conferidas |
| R11 | HDR UK Phenotype Library. *Charlson comorbidity index (Charlson 1987)*, PH1658. [Página](https://phenotypes.healthdatagateway.org/phenotypes/PH1658/detail/) | Pesos de 1987 e regras de hierarquia (metástase > malignidade; diabetes com complicação > sem) |
| R12 | CDC/NCHS. *Health, United States — Statistical reliability*. [Página](https://cdc.gov/nchs/hus/sources-definitions/statistical-reliability.htm); também [presentation standards](https://wonder.cdc.gov/controller/pdf/presentation-standards-mortality-2024.pdf) | Taxas com < 20 óbitos não são apresentadas (erro padrão relativo ≥ 23%); regra vale até os dados de 2022 |
| R13 | Definição de causa básica do Manual de preenchimento da Declaração de Óbito (Ministério da Saúde), citada em [orientações da Prefeitura de São Paulo](https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/saude/arquivos/mortalidade/Orientacoes_Preenchimento_DO_COVID-19-atualizada_2020.pdf) | Definição e seleção por regras da CID-10/OMS, via resumo de busca. Manual original não aberto |
| R14 | Conner-Spady BL, Arnett G, McGurran JJ, Noseworthy TW; Steering Committee of the Western Canada Waiting List Project. *Prioritization of patients on scheduled waiting lists: validation of a scoring system for hip and knee arthroplasty.* Can J Surg. 2004;47(1):39–46. [PMC3211810](https://pmc.ncbi.nlm.nih.gov/articles/PMC3211810) | Texto: 7 critérios (dor ao movimento, dor em repouso, marcha, limitação funcional, exame físico, progressão radiográfica, ameaça à autonomia) somados com pesos |
