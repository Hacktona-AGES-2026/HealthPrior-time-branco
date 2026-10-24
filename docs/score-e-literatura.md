# Score: cada parâmetro e sua justificativa

> Para cada parâmetro do score: o valor e **por que é esse valor**. A justificativa é de um destes tipos:
>
> - **Literatura**: artigo ou diretriz conferido, citado no §6;
> - **Lógica**: argumento explícito, que dá para conferir com uma conta ou com a definição;
> - **Regra oficial**: definida pelo desafio (`data/referencias/swalis.csv` e `src/verificar_fila_priorizada.py`),
>   que é a régua da banca.
>
> Nenhum parâmetro está justificado por "preferência". O que ainda não tem justificativa está no §6,
> com a correção proposta. Código: `main` em `cd0802e`. Números: dataset da entrega (941 solicitações).

---

## 1. A fórmula completa

```
1. PONTOS      cada achado do paciente vira um ponto, com a evidência citada (campo, frase ou evento)
2. EIXOS       progressão = maior nível entre os pontos de progressão  (0 a 3)
               sintoma    = maior nível entre os pontos de sintoma     (0 a 2)
3. CLASSE      progressão 3 → A1 · 2 → A2 · 1 → B
               progressão 0 → sintoma 2 → B · 1 → C · 0 → D
4. PRAZO       A1 15 · A2 21 · B 60 · C 180 · D 360 dias
5. SCORE       score = 100 × (23/10/2026 − data_entrada_fila) / prazo        "% do prazo consumido"
6. CAMADA      1 = CID começa com C · 2 = sinal clínico de urgência · 3 = demais
7. ORDEM       camada ↑ → score ↓ → data de entrada ↑ → solicitacao_id ↑
```

Exemplo real: SOL-2023-00010, adenocarcinoma de sigmoide (C18.7).

- Progressão 2 (câncer pelo CID e biópsia), sintoma 1 (dor EVA 4) → classe A2 → prazo 21 dias.
- Score = 100 × 1.318 / 21 = 6.276,2%. Camada 1.
- Resultado: posição 1. Na fila atual (por prioridade manual) estava na posição 606.

---

## 2. Classe SWALIS

### 2.1 Estrutura

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Classificar por **dois eixos** | progressão × sintoma | O SWALIS define a urgência por dois critérios: presença de progressão rápida da doença, e grau de dor, disfunção ou incapacidade. A ferramenta canadense de fila cirúrgica usa os mesmos ingredientes: dor, função e progressão da doença | Literatura [R1], [R14] |
| **Tabela** eixo → classe | prog 3→A1, 2→A2, 1→B; sem progressão, sintoma 2→B, 1→C, 0→D | É a definição das classes em [R1]: A1 progressão rápida evidente; A2 progressão potencial; B dor/disfunção importante sem progressão; C leve/moderada; D nenhuma | Literatura [R1] |
| Eixo = **maior** nível entre os pontos | `max` | Um único achado grave já define a urgência: um paciente com obstrução é A1 mesmo sem dor. Somar pontos faria vários achados leves virarem um grave, o que a definição de [R1] não prevê. O `max` também garante que acrescentar evidência nunca rebaixa a classe | Lógica |
| Sem ponto nenhum = nível 0 | 0 | Sem evidência de progressão nem de sintoma, a definição de [R1] é exatamente a classe D | Literatura [R1] |

### 2.2 Eixo de progressão

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Obstrução, risco de vida, perda de função → **nível 3 (A1)** | pontos `obstrucao`, `risco_vida`, `perda_funcao` | A1 na tabela oficial é "risco de vida ou de perda de órgão/função", com os exemplos "obstrução com risco de estrangulamento" e "angina instável" | Regra oficial; [R1] |
| CID de nível 3 | K40.0, K40.3, K42.0, K43.0, N13.2, I20.0 | Pela CID-10 do DATASUS: hérnias **com obstrução**, hidronefrose **com obstrução** por cálculo, **angina instável**. São os exemplos de A1 da tabela oficial. A lista é a de "CID de urgência" do verificador | Regra oficial; CID-10 |
| Câncer confirmado (CID C\*) → **nível 2 (A2)** | exceto C44 | A tabela oficial dá "neoplasia maligna confirmada" como exemplo de A2 | Regra oficial |
| Biópsia positiva → **nível 2 (A2)** | qualquer data | A tabela oficial dá "biópsia positiva aguardando cirurgia" como exemplo de A2. Vale mesmo com CID não C, para pegar o câncer escondido (23 casos no dataset) | Regra oficial |
| C44 (pele não melanoma) → **nível 1 (B)** | mesmo com biópsia | A tabela oficial dá "CBC de pele" como exemplo de **B**. Como a biópsia só confirma o próprio C44, ela não sobe a classe | Regra oficial |
| Lesão incerta (D37–D48, R91) e suspeita de malignidade → **nível 1 (B)** | — | Na CID-10, D37–D48 é literalmente "neoplasia de comportamento incerto" e R91 é "achado anormal de imagem do pulmão": ainda não é câncer confirmado. A tabela oficial só põe em A2 câncer **confirmado** ou biópsia positiva. Logo a suspeita fica um nível abaixo: B, a classe mais urgente sem confirmação. Quando a biópsia confirmar, o ponto de biópsia sobe para A2 sozinho | Lógica + regra oficial |

### 2.3 Eixo de sintoma

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Dor EVA 7–10 → **nível 2** | ≥ 7 | Em escala visual analógica, ≥ 6,5 corresponde a interferência **grave** na função. Na escala inteira de 0 a 10, isso é 7 a 10 | Literatura [R3] |
| Dor EVA 4–6 → **nível 1** | 4 a 6 | 3,5–6,4 = interferência **moderada** [R3]; na escala inteira, 4 a 6 | Literatura [R3] |
| Dor EVA 0–3 → **nível 0** | ≤ 3 | ≤ 3,4 = interferência **leve** [R3]. É também o corte de "sem urgência" do verificador oficial | Literatura [R3]; regra oficial |
| Limitação grave → 2 · moderada → 1 · nenhuma/leve → 0 | — | O campo do dataset usa as mesmas palavras das classes: B = disfunção "importante", C = "moderada", D = "sem disfunção relevante". O verificador trata nenhuma/leve como sem urgência | Literatura [R1]; regra oficial |
| Dor ou limitação **não informada** → nível 1 | 1 | Falta de dado não é ausência de dor. Com nível 0, o paciente poderia ir para D (prazo de 360 dias) por falha de cadastro. Com nível 2, uma lacuna viraria urgência. O nível 1 é o meio da escala: não pune nem infla, e o paciente ganha alerta de cadastro incompleto | Lógica |
| Varizes com úlcera (I83.2) e colelitíase com colecistite aguda (K80.0) → **nível 2 (B)** | — | Pela CID-10, são complicações da doença de base. A tabela oficial põe "colelitíase com colecistites de repetição" em **B** e "varizes com dor" em C; com úlcera e inflamação é mais que dor, então B | Regra oficial; CID-10 |

### 2.4 Leitura do texto clínico

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Termos de alarme | 33 termos (colangite, encarceramento, melena, perda ponderal…) | São os termos que o verificador oficial usa para definir urgência. Cada termo vai para o ponto cuja descrição na tabela oficial ele descreve (ex.: colangite e sepse são "risco de vida") | Regra oficial |
| Negação | "sem", "nega", "ausência de", "não há", "descarta"… antes do termo | O NegEx mostrou que gatilhos de negação antes do achado, com escopo limitado, identificam achados negados em texto clínico | Literatura [R8] |
| Escopo da negação | até o fim da oração (pontuação, "mas", "porém", "evoluiu") | O NegEx limita o escopo a até 6 palavras. Usamos a oração porque em "Sem melhora, evoluiu com suboclusão" a negação não pode alcançar a suboclusão. Na dúvida, o erro escolhido é **não** apagar urgência: perder um sinal grave custa mais que revisar um a mais | Literatura [R8] + lógica |
| Jev conta com **p ≥ 0,7** | 0,7 | O Jev escolhe entre 9 opções (8 pontos + "nenhum"); o acaso daria 0,11. Com p ≥ 0,7, a categoria tem mais probabilidade que todas as outras somadas (> 0,5) e 6 vezes o acaso | Lógica |
| Jev vai para **revisão humana** com 0,4 ≤ p < 0,7 | 0,4 | Entre 0,4 e 0,7 a categoria é plausível (3,6 vezes o acaso), mas não é maioria. Então não muda a classe e vai para o regulador decidir | Lógica |
| Jev **só sobe** a classe | consequência do `max` | O LLM aponta e cita a frase; quem decide é a tabela. Sem o Jev a classe é a das regras; com ele, só pode ficar igual ou maior | Lógica |

**Evidência do projeto (Jev):** em 36 frases reescritas fora do padrão do dataset, a classe certa sobe de
25% (só palavra-chave) para 92% (palavra-chave + Jev). A amostra é pequena e foi escrita pelo time
(`docs/swalis.md`).

**Resultado:** A1 102 · A2 166 · B 225 · C 326 · D 122.

---

## 3. Prazo e score

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Prazo B, C, D | 60, 180, 360 dias | Iguais aos tempos máximos do SWALIS publicado | Literatura [R1]; regra oficial |
| Prazo A1, A2 | 15, 21 dias | Tabela oficial do desafio. O artigo usa 8 e 30 dias; o desafio adaptou a tabela. A ordem A1 < A2 < B se mantém | Regra oficial |
| **Score = % do prazo** | `100 × dias / prazo` | É o score do SWALIS: em [R1], P(t) = dias × (prazo de D / prazo da classe) = dias × 360 / prazo = **3,6 × score**. Mesma ordem, só muda a escala. O artigo chama isso de "dias de espera ajustados pela necessidade" | Literatura [R1] |
| Envelhecimento diário | +100/prazo por dia | O score sobe sozinho: A1 +6,67/dia, A2 +4,76, B +1,67, C +0,56, D +0,28. Quem espera sobe sem depender de ninguém, e quem tem doença mais urgente sobe mais rápido | Literatura [R1] + lógica |
| 100% = prazo estourado | — | 100% significa o mesmo em qualquer classe: o paciente esperou tudo o que a doença tolera. Por isso dá para comparar classes diferentes pelo mesmo número | Lógica |
| Data de referência fixa | 23/10/2026 | Mesma entrada → mesma fila. Com a data do relógio, o resultado mudaria a cada execução e não seria auditável | Lógica |
| Score editado pelo regulador | substitui o do sistema | O médico regulador tem a palavra final. Ele edita o score, e não a posição, porque a posição muda todo dia | Lógica |

---

## 4. Camada e ordem

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| **Camada 1 = CID começa com C** | pelo CID, nunca pela flag | É a regra de ouro do desafio: oncológico pelo CID nunca abaixo de paciente sem urgência. A flag do dataset está errada em 44 casos; o CID é o dado clínico | Regra oficial |
| **Camadas em vez de peso** | ordem lexicográfica | Prova: o score não tem teto. Uma hérnia D com 1.500 dias tem 416,7%, e um CBC de pele B com 15 dias tem 25%. Qualquer peso finito pode ser superado pelo tempo. Pondo a camada como **primeira** chave da ordenação, todo oncológico fica acima de todo não oncológico, **para qualquer valor de score**. O verificador oficial confirma | Lógica |
| Camada 2 = sinal clínico de urgência | CID de complicação, piora durante a espera (PS, internação, progressão em imagem, reavaliação com piora), biópsia positiva, termo de alarme | São exatamente os sinais que o verificador oficial usa para dizer que o paciente **tem** urgência | Regra oficial |
| Dor e limitação **não** definem a camada 2 | — | Dor e limitação já entram na classe (eixo de sintoma, B/C). Usá-las de novo na camada contaria o mesmo dado duas vezes. A camada 2 é para sinais de que o risco **aumentou**. A regra de ouro não muda, porque todo oncológico já está na camada 1 | Lógica |
| Evento antes da entrada na fila não conta como piora | — | A camada 2 é para piora **durante a espera**; o que veio antes é a história que gerou a indicação | Lógica |
| Evento duplicado não conta | — | O mesmo atendimento registrado duas vezes não é piora em dobro | Lógica |
| Dentro da camada: **score decrescente** | — | Ordem do SWALIS por prioridade P(t) | Literatura [R1] |
| Desempate: **entrada mais antiga** | — | Em [R1], na mesma classe, quem esperou mais é atendido antes | Literatura [R1] |
| Último desempate: `solicitacao_id` | — | Só garante que duas execuções dão a mesma ordem | Lógica |

**Resultado:** camadas 177 / 206 / 558; verificador oficial aprovado.

---

## 5. Fatores contextuais: comorbidade e idade/mortalidade

**Estado no código:** os dois fatores são calculados (`score/`) e ficam em `data/processed/`, mas **ainda
não multiplicam o score da fila**. As justificativas abaixo valem para quando forem ligados.

### 5.1 Comorbidade (Charlson)

```
charlson = soma dos pesos das categorias Charlson achadas em comorbidades + CID secundário
fator    = 1,00 (0) · 1,03 (1) · 1,06 (2) · 1,10 (3–4) · 1,15 (≥ 5)
```

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Índice de Charlson | — | Índice de comorbidade validado para prever mortalidade: em 1 ano, 12% com escore 0, 26% com 1–2, 52% com 3–4 e 85% com ≥ 5 | Literatura [R5] |
| Pesos | IAM 1, ICC 1, pulmonar crônica 1, diabetes 1, renal 2, tumor 2, linfoma/leucemia 2, metástase 6 | São os pesos publicados | Literatura [R5], [R11] |
| **Sem idade** no Charlson | — | No índice combinado, 1 ponto de comorbidade equivale a cerca de 1 década de idade. A idade já entra no fator de mortalidade, então somá-la aqui contaria a idade duas vezes | Literatura [R6] + lógica |
| **Sem o CID principal** | — | O Elixhauser separa comorbidades do motivo principal da internação. Aqui o motivo é a doença da cirurgia, que já está na classe | Literatura [R10] + lógica |
| Cada categoria conta uma vez | — | A mesma doença no texto e no CID secundário é uma doença só | Lógica |
| Faixas 3–4 e ≥ 5 | — | São as faixas do artigo original (0, 1–2, 3–4, ≥ 5) | Literatura [R5] |
| Faixas 1 e 2 separadas | 1,03 e 1,06 | O artigo agrupa 1–2; separamos para o fator subir um degrau a cada ponto nas faixas mais comuns (331 pacientes com 1, 89 com 2) | Lógica |
| Fator **cresce** com o Charlson | 1,00 → 1,15 | A mortalidade cresce com o escore [R5], então o fator tem de crescer junto e parar na faixa máxima (≥ 5) | Literatura [R5] + lógica |
| Charlson 0 → **1,00** (nunca reduz) | piso 1,00 | Não achar comorbidade no texto não prova que ela não existe. O fator só reconhece risco e nunca dá desconto | Lógica |
| **Teto 1,15** | máx. 1,15 por fator | Ver o argumento do teto no §5.3 | Lógica |

### 5.2 Idade e mortalidade (IRR)

```
taxa(cid, faixa) = óbitos com causa básica = cid na faixa / população da faixa     (SIM 2019–2023 / IBGE)
IRR              = taxa(cid, faixa) / taxa do mesmo cid em todas as idades
fator            = 1,00                                     se IRR ausente, 0 ou ≤ 1
                   min(1,15 ; 1 + 0,075 × min(log2 IRR ; 2))  se IRR > 1
```

| Parâmetro | Valor | Justificativa | Base |
|---|---|---|---|
| Causa básica do SIM | `CAUSABAS` | Causa básica é a doença que iniciou a cadeia de eventos que levou à morte, escolhida por regra da OMS/CID-10. Mede quanto aquela doença mata | Literatura [R13] |
| Taxa (óbitos / população) | — | Comparar faixas etárias exige dividir pela população de cada faixa. Contagem bruta só mostraria qual faixa tem mais gente | Lógica |
| IRR = taxa da faixa / taxa média do CID | — | Compara o paciente com o próprio CID: diz se, **para essa doença**, a idade dele é de maior risco que a média. Ex.: C18 aos 70–79 anos dá 38,4 contra 6,5 por 100 mil, IRR 5,92 | Lógica |
| CID com 3 caracteres | C18.7 → C18 | Subcategorias têm poucos óbitos por faixa. Agrupar na categoria dá taxas mais estáveis | Lógica |
| Faixas 40–49, 50–59, 60–69, 70–79, 80+ | décadas | São as mesmas décadas do ajuste por idade do Charlson (1 ponto por década a partir dos 50) | Literatura [R6] |
| Faixas 0–17 e 18–39 | — | 0–17 é a idade pediátrica (menor de 18 anos). Em 18–39, **todos** os 51 CIDs da tabela têm IRR ≤ 1, então o fator é 1,00 de qualquer jeito: dividir em décadas não mudaria nenhum paciente (conferido na tabela do repo) | Lógica (dados) |
| Escala **log2** | — | Razão de taxas é multiplicativa: dobrar o risco tem de valer o mesmo degrau, seja de 1 para 2 ou de 2 para 4. No log2, cada duplicação vale +0,075 | Lógica |
| Saturação em **IRR 4** | `min(log2 IRR; 2)` | No dataset, o IRR mediano é 1,15 e o percentil 75 é 4,08. Saturar em 4 faz só o quarto de maior risco atingir o teto | Lógica (dados) |
| **0,075** por duplicação | — | Consequência do teto e da saturação: 0,15 / 2 duplicações = 0,075 | Lógica |
| IRR ≤ 1 → **1,00** | piso | IRR abaixo de 1 é uma média da população, não uma proteção individual. Reduzir o score por isso puniria o paciente com um dado que não é dele | Lógica |

### 5.3 Por que o teto é 1,15 (vale para os dois fatores)

```
menor razão entre prazos de classes vizinhas = 21 / 15 = 1,40   (A2 / A1)
produto máximo dos dois fatores              = 1,15 × 1,15 = 1,3225 < 1,40
```

Com o mesmo tempo de espera, um paciente da classe menos urgente tem score no máximo 1/1,40 do score
do paciente da classe vizinha mais urgente. Como os fatores multiplicam no máximo por 1,3225, **eles nunca
fazem uma classe menos urgente passar uma mais urgente com o mesmo tempo de espera**. Ou seja, o fator
ajusta a ordem **dentro** da urgência e nunca substitui a classe. Com qualquer teto acima de
√1,40 ≈ 1,183 por fator, essa garantia deixa de valer.

---

## 6. O que ainda não tem justificativa (e como corrigir)

| Ponto | Problema | Correção proposta |
|---|---|---|
| IRR sem limiar mínimo de óbitos | O CDC/NCHS não publica taxa com menos de 20 óbitos: o erro relativo passa de 23% [R12]. Na tabela, 107 de 357 células têm menos de 20 óbitos, e 26 pacientes recebem fator > 1 vindo delas | Fator 1,00 quando a célula tiver menos de 20 óbitos |
| Hierarquia do Charlson | Pela regra do índice, metástase substitui "tumor" e diabetes com complicação substitui sem complicação [R11]; o código soma os dois | Aplicar a hierarquia (0 casos no dataset hoje) |
| Teto `min(100, …)` da composição do `score/README.md` | O score da fila passa de 100 (6.276% no exemplo); o teto empataria todos os atrasados | Multiplicar o % do prazo **sem** teto; a garantia do §5.3 já limita o efeito |
| Prazos A1 e A2 | Diferentes do artigo (8 e 30 dias) | Manter a tabela oficial (é a régua da banca) e dizer "adaptado do SWALIS" |

---

## 7. Referências (todas conferidas)

| ID | Referência | O que foi lido |
|---|---|---|
| R1 | Valente R, Testi A, Tanfani E, Fato M, Porro I, Santo M, Santori G, Torre G, Ansaldo G. *A model to prioritize access to elective surgery on the basis of clinical urgency and waiting time.* BMC Health Serv Res. 2009;9:1. doi:[10.1186/1472-6963-9-1](https://doi.org/10.1186/1472-6963-9-1) | Texto completo ([PMC2651867](https://pmc.ncbi.nlm.nih.gov/articles/PMC2651867)): classes, prazos 8/30/60/180/360, P(t) = (t − t0) × γ, critérios |
| R3 | Boonstra AM, Schiphorst Preuper HR, Balk GA, Stewart RE. *Cut-off points for mild, moderate, and severe pain on the visual analogue scale for pain in patients with chronic musculoskeletal pain.* Pain. 2014;155(12):2545–2550. doi:[10.1016/j.pain.2014.09.014](https://doi.org/10.1016/j.pain.2014.09.014) | Resumo: ≤ 3,4 / 3,5–6,4 / ≥ 6,5 (interferência na função) |
| R5 | Charlson ME, Pompei P, Ales KL, MacKenzie CR. *A new method of classifying prognostic comorbidity in longitudinal studies: development and validation.* J Chronic Dis. 1987;40(5):373–383. [PubMed 3558716](https://pubmed.ncbi.nlm.nih.gov/3558716/) | Resumo: mortalidade em 1 ano 12% / 26% / 52% / 85% para 0 / 1–2 / 3–4 / ≥ 5 |
| R6 | Charlson M, Szatrowski TP, Peterson J, Gold J. *Validation of a combined comorbidity index.* J Clin Epidemiol. 1994;47(11):1245–1251. doi:[10.1016/0895-4356(94)90129-5](https://doi.org/10.1016/0895-4356(94)90129-5) | Resumo: 1 ponto ≈ 1 década de idade; pontos por década conferidos em fonte secundária |
| R8 | Chapman WW, Bridewell W, Hanbury P, Cooper GF, Buchanan BG. *A simple algorithm for identifying negated findings and diseases in discharge summaries.* J Biomed Inform. 2001;34:301–310. [PDF](https://www.dbmi.pitt.edu/wp-content/uploads/2022/10/A-simple-algorithm-for-identifying-negated-findings-and-diseases-in-discharge-summaries.pdf) | Resumo: gatilhos de negação com escopo de 1 a 6 palavras |
| R10 | Elixhauser A, Steiner C, Harris DR, Coffey RM. *Comorbidity measures for use with administrative data.* Med Care. 1998;36(1):8–27. [PubMed 9431328](https://pubmed.ncbi.nlm.nih.gov/9431328/) | Resumo: comorbidades separadas do motivo principal da internação |
| R11 | HDR UK Phenotype Library. *Charlson comorbidity index (Charlson 1987)*, PH1658. [Página](https://phenotypes.healthdatagateway.org/phenotypes/PH1658/detail/) | Pesos de 1987 e regras de hierarquia |
| R12 | CDC/NCHS. *Health, United States: statistical reliability.* [Página](https://cdc.gov/nchs/hus/sources-definitions/statistical-reliability.htm) | Taxa com menos de 20 óbitos não é apresentada (erro relativo ≥ 23%) |
| R13 | Definição de causa básica do Manual de preenchimento da Declaração de Óbito (Ministério da Saúde), reproduzida em [orientação da Prefeitura de São Paulo](https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/saude/arquivos/mortalidade/Orientacoes_Preenchimento_DO_COVID-19-atualizada_2020.pdf) | Definição e seleção pela CID-10/OMS |
| R14 | Conner-Spady BL, Arnett G, McGurran JJ, Noseworthy TW; Steering Committee of the Western Canada Waiting List Project. *Prioritization of patients on scheduled waiting lists: validation of a scoring system for hip and knee arthroplasty.* Can J Surg. 2004;47(1):39–46. [PMC3211810](https://pmc.ncbi.nlm.nih.gov/articles/PMC3211810) | Texto: critérios de dor, função e progressão somados com pesos |

**Regra oficial do desafio:** `data/referencias/swalis.csv` (classes, prazos e exemplos), `src/verificar_fila_priorizada.py`
(regra de ouro, CID de urgência, termos de alarme, eventos de piora) e tabelas CID-10 do DATASUS em
`data/referencias/CID10CSV/`.

Detalhe técnico de cada parâmetro (arquivo:linha) e dos que não fazem parte do score (inbox, alertas):
[`auditoria-parametros.md`](auditoria-parametros.md).
