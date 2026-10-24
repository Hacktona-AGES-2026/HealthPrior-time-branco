# DECISOES.md — HealthPrior (Time Branco)

Registro das decisões do time e das solicitações que ficaram fora do `fila_priorizada.csv`.
Decisões de fluxo detalhadas em `docs/fluxo-sistema.md` §10.

## Decisões

| ID | Data | Decisão | Motivo | Alternativa descartada | Componente |
|---|---|---|---|---|---|
| D-01 | 2026-10-24 | Carga inicial não passa pelo regulador; classe fica "sugerida, não confirmada" | Inviável revisar 941 casos | Regulador revisar tudo | C-02 |
| D-02 | 2026-10-24 | Evento sem mudança de classe só é registrado | Atualização diária já reordena; evita fadiga de alertas | Reordenar e notificar a cada evento | C-08 |
| D-03 | 2026-10-24 | Regulador edita classe ou score, não posição; flag `editado_manualmente` | Posição muda todo dia; score editado envelhece | Fixar posição | C-10 |
| D-04 | 2026-10-24 | Pré-processamento único para carga e eventos | Mesmas regras em lote e contínuo | Dois pipelines | C-05 |
| D-05 | 2026-10-24 | Inconsistências são sinalizadas, nunca apagadas | Auditabilidade | Remover registros | C-05, C-06 |
| D-06 | 2026-10-24 | Regra de ouro como camadas, não peso | Restrição dura | Peso alto no score | C-11 |
| D-07 | 2026-10-24 | Verificador é portão de publicação | Violação é eliminatória | Publicar e corrigir depois | C-12 |
| D-08 | 2026-10-24 | Aprendizado propõe regras; comitê aprova; versões | Controle humano | Retreino automático | C-14 |
| D-09 | 2026-10-24 | SWALIS interno documentado à parte | Separação de responsabilidades | — | C-07 |
| D-10 | 2026-10-24 | Duplicatas fundidas mantendo a data de entrada mais antiga | Favorece o paciente | Manter a mais recente | C-05 |
| D-11 | 2026-10-24 | Stack: FastAPI + pandas no back; React (Vite + TS) no front (banco: ver D-15) | Conhecimento do time; rapidez | — | todos |
| D-12 | 2026-10-24 | Sem login: seletor de persona e de usuário fixo no front | Hackathon; o log ainda registra autores distintos | Autenticação real | US-23 |
| D-13 | 2026-10-24 | API é a fronteira back × front; back sobe mocks com o contrato final primeiro | Trabalho em paralelo sem retrabalho | Front esperar o back | US-01..US-23 |
| D-14 | 2026-10-24 | Backend em Clean Architecture enxuta (domain / application / infrastructure / api), com teste que protege a regra de dependência | Separar regra clínica de detalhe técnico; trocar SWALIS stub pelo real sem mexer no resto | Rotas com regra de negócio direto no banco | backend |
| D-15 | 2026-10-24 | Banco: PostgreSQL 16 (Docker) com SQLModel/SQLAlchemy 2, no lugar do SQLite | Banco de verdade para o pitch; concorrência (API + CLI) sem travar arquivo; upsert nativo para a carga idempotente | SQLite (simples, mas limitado para a demo); DuckDB (analítico, escrita de um processo só) | US-01 |
| D-16 | 2026-10-24 | Sem migrations (Alembic): tabelas criadas com `create_all`; mudança de schema = `docker compose down -v` e recarga | Hackathon; dados são reproduzíveis a partir dos CSVs | Alembic | US-01 |
| D-17 | 2026-10-24 | `eventos.solicitacao_id` sem chave estrangeira | Eventos órfãos existem no dataset e nada é apagado (I-03); a US-04 os sinaliza | FK (rejeitaria os órfãos na carga) | US-01 |
| D-18 | 2026-10-24 | `correcoes_log` registra mudanças de valor visíveis (município, prioridade, CID com minúscula/espaço). Chaves de comparação (`cid_norm` sem ponto, `nome_norm`) não geram log | 816 dos 941 CIDs têm ponto e quase todo nome difere só na caixa: ~1.700 linhas de ruído sem informação. O original fica sempre intacto na coluna de origem | Logar toda diferença entre original e `*_norm` (cumpre o CA "toda correção" ao pé da letra) | US-02 |
| D-19 | 2026-10-24 | `municipio_norm` usa o nome oficial do IBGE **com acento** (Gravataí, Osório, Viamão), via tabela fixa em `domain/preprocessing/municipios.py` com os 38 municípios do dataset; município fora da tabela só perde espaços sobrando | PRE-03 pede o nome oficial; o dataset vem sem acento | Forma canônica sem acento (só unifica a caixa) | US-02 |
| D-20 | 2026-10-24 | A normalização roda dentro da carga (mesma transação) e também avulsa (`python -m app.cli normalizar`). Recalcula as colunas `*_norm` e refaz o log de PRE-01..04, sem tocar nas outras regras | D-04: mesmo pré-processamento para carga e eventos; evita carga sem normalizar | Só comando separado | US-02 |
| D-21 | 2026-10-24 | `nome_norm` = minúsculo, sem acento, espaços colapsados; prioridade desconhecida vira vazia e é registrada no log | PRE-02 e PRE-04 não definem o formato; é só chave de comparação | Maiúsculo; rejeitar a carga com prioridade inválida | US-02 |
| D-22 | 2026-10-24 | ~~Camada 2 = complemento exato de "sem urgência" do verificador~~ (revista por D-27) | Mais seguro em relação à regra oficial | Camada 2 só com sinais clínicos | US-08 |
| D-23 | 2026-10-24 | Eventos de piora só contam durante a espera e não duplicados | Coerente com PRE-07/08 | Contar qualquer evento | US-08 |
| D-24 | 2026-10-24 | Câncer escondido (biópsia positiva, CID não C) vai para a camada 2 com alerta "revisar CID"; biópsia positiva conta em qualquer data | Sem a exceção, D-23 apagaria esses casos; camada 1 continua só pelo CID (Q-08 aberta) | Camada 1 pela biópsia | US-08 |
| D-25 | 2026-10-24 | Desempate na camada: score desc, entrada mais antiga, solicitacao_id | Ordem determinística; 80+ aguarda Q-10 | Desempate por idade | US-08 |
| D-26 | 2026-10-24 | CSV provisório gerado direto do dataset (sem banco) com SWALIS stub: `python -m app.cli gerar-fila-csv` | Garantir a entrega das 14h sem depender da US-01 | Esperar a US-01 | US-08/09/10 |
| D-27 | 2026-10-24 | **Revisa D-22.** Camada 2 = só sinais clínicos (CID de complicação, evento de piora na espera, biópsia positiva, alarme no texto). Dor > 3 e limitação moderada/grave viram "sintomas": aparecem na justificativa e ficam para o SWALIS (classe), sem definir camada | Com D-22, 320 dos 526 da camada 2 (61%) estavam lá só por sintoma e competiam com quem piorou; dor é autorrelatada e já é critério da classe SWALIS. A regra de ouro não muda (camada 1). Resultado: camada 2 de 526 → 206; PS/internação recente na 1ª metade de 50% → 100% | Manter D-22; 4 camadas (onco / clínico / sintomático / demais) | US-08 |
| D-28 | 2026-10-24 | Piora clínica (PRE-06) = qualquer evento, durante a espera e sem ser duplicado, de PS, internação, imagem com progressão, reavaliação com piora ou paciente que relata piora. Sem janela de recência. No dataset: 199 pacientes com piora, 147 com flag "nao" corrigida | Alinha com os sinais da camada 2 e com o gatilho `relata_piora` (C-03). A US-03 pede "durante a espera", não "recente" | Só PS/internação (103 pacientes, 66 com flag "nao"); janela de 180 dias | US-03 |
| D-29 | 2026-10-24 | `piora_recalculada` = piora por evento **ou** flag original "sim": só corrige "nao" → "sim", nunca rebaixa. 36 flags "sim" ficam sem evento de apoio | A piora pode estar só no texto (SOL-2026-00637); silêncio não é estabilidade (I-08). A análise de texto (LLM) refina depois | Recalcular só por evento (rebaixaria "sim" sem evidência) | US-03 |
| D-30 | 2026-10-24 | Evento duplicado (PRE-07) = mesma solicitação, data, tipo, resultado, valor, descrição **e origem**. Fica o de menor `evento_id`; os outros recebem `duplicado_de` e não contam como piora. Nenhum é apagado. No dataset: 6 | EVT-000712/713 diferem só na origem (PS São Lucas × UPA) e podem ser dois atendimentos reais; apagar um é irreversível para o score. **O `csv_source.py` provisório (D-26) ignora a origem e acha 7**: alinhar quando ele passar a usar `marcar_eventos` | Ignorar a origem (7 duplicatas) | US-03 |
| D-31 | 2026-10-24 | Evento histórico (PRE-08) = `data_evento` **anterior** à `data_entrada_fila` (no dia da entrada já é espera). Evento órfão não é histórico nem duplicado. No dataset: 155. O "104 com PS/internação recente" do `fluxo-sistema.md` §12 inclui 1 paciente que só tem PS histórico; o número correto é 103 (66 com flag "nao") | A data de entrada é o corte da espera; sem solicitação não há corte | Contar o dia da entrada como histórico | US-03 |
| D-32 | 2026-10-24 | As flags (`RecalcularFlags`) rodam na carga, depois da normalização e na **mesma transação** (D-20), e também avulsas (`python -m app.cli flags`). Refazem só o log das suas regras (PRE-05/06) em `correcoes_log` | D-04: mesmo pré-processamento para carga e eventos; reprocessar não duplica o log; carga, normalização e flags entram juntas ou não entram | Comando só separado; transação própria | US-03 |
| D-34 | 2026-10-24 | PRE-10 (contato perdido) = 2 ou mais `nao_atendeu` durante a espera e sem duplicados, ou observação "número não existe" (39 pacientes, bate com o doc). PRE-11 (sem telefone) = observação cita ACS ou "sem telefone" (28, bate com o doc: 18 "não possui telefone", 2 "sem telefone próprio", 8 "ACS informa que mudou de endereço"). PRE-12 (câncer escondido) = biópsia positiva não duplicada + CID não `C` (23, bate com o doc; biópsia anterior à entrada conta, é a que originou a solicitação). Nenhuma altera prioridade nem tira o paciente da fila | Reproduzem os números do `fluxo-sistema.md`; contato perdido pode ser barreira de acesso e não pune. A subida de classe do PRE-12 segue o fluxo de eventos (US-08, D-24) | Contar também texto "sem sucesso" como tentativa (mesmo conjunto de 39) | US-05 |
| D-35 | 2026-10-24 | PRE-13 (diabetes fora do cadastro) = `flag_diabetico` ≠ "sim" e sem DM nas comorbidades e (observação "não consta no cadastro / sem registro no cadastro / investigar DM" ou HbA1c ≥ 6,5% em evento ou no cadastro): 18 pacientes (17 por texto, +1 por HbA1c). Não altera prioridade (HbA1c não entra no score, regra 7) | 6,5% é o critério diagnóstico de diabetes; texto explícito sozinho deixaria 1 de fora | Só texto explícito (17) | US-05 |
| D-36 | 2026-10-24 | PRE-14 (justificativa sem conteúdo) = vazia, ou abre com frase genérica ("Solicito cirurgia", "Indicação cirúrgica", "Conforme laudo anexo", "Paciente com indicação de X") e tem menos de 60 caracteres: 50 pacientes. PRE-15 (campo vazio) = `prioridade_regulacao`, `intensidade_dor_eva`, `asa` ou `distancia_hospital_km` sem valor: 93 pacientes, um alerta por paciente listando os campos. **PRE-14 e PRE-15 só geram alerta, sem pendência** (a tabela de C-05 diz "alerta"; o texto da US-05 dizia pendência para todas). `limitacao_funcional` (20 vazios) fica fora: não consta na regra | Evita 140+ pendências de baixo valor na tela do administrativo; não inventar campo fora da regra | Pendência em todas; só menos de 50 caracteres (45) | US-05 |
| D-37 | 2026-10-24 | Alertas em `Solicitacao.alertas`: `contato_perdido`, `contato_via_acs`, `revisar_cid`, `diabetes_fora_do_cadastro`, `informacao_insuficiente`, `cadastro_incompleto`. Reprocessar troca só esses; alertas de outras regras ficam | O contrato (`GET /fila`) usa slugs, ex.: `contato_perdido`; várias US escrevem no mesmo campo | Sobrescrever a lista toda | US-05 |
| D-38 | 2026-10-24 | Pendências automáticas (PRE-10..13): uma por (solicitação, regra), ids `PEN-0001…` estáveis, `aberta_em` = REF. Reprocessar abre as novas, atualiza a evidência das abertas e **encerra** (resolvida, por "sistema", resolução "deixou_de_valer") as abertas cujo achado sumiu. Nunca reabre nem altera pendência que uma pessoa resolveu ou descartou, e nunca apaga | Idempotência sem passar por cima do trabalho do administrativo (I-03) | Recriar todas a cada carga; reabrir as descartadas se o achado persistir | US-05 |
| D-39 | 2026-10-24 | A detecção (`DetectarInconsistencias`) roda na carga depois das flags, na mesma transação (D-32), e avulsa (`python -m app.cli inconsistencias`). Precisa vir depois das flags porque PRE-10/12/13 ignoram eventos duplicados | Carga, normalização, flags e inconsistências entram juntas ou não entram | Rodar antes das flags | US-05 |

## Solicitações fora da fila

> Preencher ao gerar a entrega. O verificador avisa quantas solicitações ficaram de fora; cada uma precisa de motivo.

| Motivo (regra) | Quantidade | Solicitações | Observação |
|---|---|---|---|
| Duplicata (PRE-20) | | | Mantida a de entrada mais antiga |
| Operou em outro serviço / convênio (PRE-21/22) | | | |
| Desistência (PRE-23) | | | |

## Premissas e limitações

- Dados 100% sintéticos; nenhum número aqui é evidência clínica.
- Pesos e prazos por procedimento são provisórios até validação com os mentores.
