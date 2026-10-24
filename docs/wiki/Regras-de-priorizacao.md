# Regras de priorização

Fonte detalhada: [`docs/swalis.md`](../swalis.md), [`docs/score-e-literatura.md`](../score-e-literatura.md) e
[`DECISOES.md`](../../DECISOES.md).

## Classes SWALIS e prazos
| Classe | Prazo máximo |
|---|---|
| A1 | 15 dias |
| A2 | 21 dias |
| B | 60 dias |
| C | 180 dias |
| D | 360 dias |

A classe diz quanto tempo a doença tolera esperar. **Mudar a classe é julgamento clínico**: o sistema só a sugere
(`sugerida_nao_confirmada`) e ela só vale depois do regulador (exceto na carga inicial, que fica marcada como não confirmada).

## Como a classe é sugerida (duas etapas)
1. **Pontos**, cada um com a evidência citada: campos do cadastro (CID, dor EVA, limitação, eventos), palavras-chave
   **com tratamento de negação** e, quando há chave, o LLM (Jev), que aponta a frase e o ponto que ela descreve.
   O LLM só **sobe** a classe, nunca desce, e só vale se a frase existir literalmente e não estiver negada.
2. **Decisão por regras determinísticas:** o eixo de progressão (0 a 3) e o de sintoma (0 a 2) tomam o **maior** nível
   entre os pontos, e a tabela SWALIS devolve A1 a D.

Cada motivo mostrado ao regulador diz o ponto, a frase ou campo e a origem (`regra`, `palavra-chave` ou `Jev p=…`).

## Score e ordenação
`score = % do prazo × fator de comorbidade × fator de idade/IRR`, em que o % do prazo é `100 × dias na fila ÷ prazo da classe`.
Cada fator vai de 1,00 a 1,15 e só desempata dentro da urgência: com o mesmo tempo de espera, nenhum fator inverte
classes vizinhas (D-103).

## Camadas
| Camada | Quem | 
|---|---|
| **1** | Oncológicos (pelo CID, não pela flag) |
| **2** | Urgentes não oncológicos: CID de complicação, evento de piora durante a espera, biópsia positiva ou sinal de alarme no texto |
| **3** | Os demais, sem sinais clínicos de urgência |

As camadas 1 e 2 formam um bloco único ordenado pelo score; a 3 fica abaixo (D-112). Dentro de cada bloco manda o
score. A justificativa de cada linha inclui a camada, os motivos, a classe, o prazo, a versão das regras e o % do prazo.

## Regra de ouro (eliminatória)
Nenhum paciente com neoplasia maligna (CID iniciado por `C`) pode ficar abaixo de um paciente **sem urgência clínica**.
É garantida na trava (`domain/ranking.py`) e conferida de novo pelo verificador oficial antes de publicar.

## Invariantes
| ID | Regra |
|---|---|
| I-01 | Regra de ouro, em qualquer caminho: score, edição manual, carga, atualização diária e regras aprendidas |
| I-02 | Oncológico nunca é rebaixado nem suspenso automaticamente; só por decisão humana registrada |
| I-03 | Nada é apagado; toda saída da fila tem motivo, autor e data |
| I-04 | Mudança de classe sempre tem decisão humana (exceto a carga inicial, não confirmada) |
| I-05 | O LLM extrai e cita; nunca decide classe nem altera CID sozinho |
| I-06 | Regras do SWALIS só mudam via comitê, com versão e impacto simulado |
| I-07 | Fila que não passa no verificador não é publicada |
| I-08 | Ausência de eventos não é estabilidade (gera recontato) |
| I-09 | Usar o CID, não a flag, para decidir oncológico |
| I-10 | Toda correção automática registra o valor original |

## Ciclo de aprendizado
As justificativas dos reguladores são agrupadas por procedimento, motivo e troca de classe. Quando vários
reguladores distintos fazem a mesma mudança, vira uma **proposta** de regra. O comitê aprova ou rejeita; propostas
que **rebaixariam** um procedimento com paciente oncológico ativo são bloqueadas antes de chegar ao comitê (I-01).
Uma regra aprovada pode ser **revertida** (`POST /regras/{id}/reverter`). Detalhes: US-18 e US-19 em
[`docs/user-stories.md`](../user-stories.md).
