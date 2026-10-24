# Fatores de score: mortalidade e comorbidade

Esta pasta produz dois fatores explicáveis para cada solicitação da fila. Eles
não ordenam a fila e não alteram `score_sistema`; são insumos auditáveis para
uma composição posterior.

```text
score externo (JEV) ─┐
                      ├─ composição experimental ─> score proposto
comorbidade ──────────┤
mortalidade ──────────┘
```

## Contrato proposto de composição

Se `score_jev` for um score relativo entre 0 e 100, a proposta é:

```text
score_proposto = min(100, score_jev × multiplicador_comorbidade × multiplicador_idade_mortalidade)
```

| Campo | Origem | Faixa |
| --- | --- | --- |
| `score_jev` | Modelo externo JEV | Contrato esperado: 0–100 |
| `multiplicador_comorbidade` | `apply_comorbidity_multiplier.py` | 1,00–1,15 |
| `multiplicador_idade_mortalidade` | `apply_idade_mortality_multiplier.py` | 1,00–1,15 |
| `score_proposto` | Composição acima | 0–100 |

Exemplo: `score_jev = 72`, comorbidade `1,06` e mortalidade `1,148`:

```text
score_proposto = min(100, 72 × 1,06 × 1,148) = 87,64
```

> Se o JEV entregar uma **probabilidade** (0–1), esta multiplicação não deve
> ser usada: a combinação precisa ser feita em log-odds e calibrada com
> desfechos. Se o JEV for o LLM `typesafe/jev-1.14` documentado neste projeto,
> ele só produz alertas e não pode alterar classe ou score. Portanto,
> `score_proposto` é uma proposta experimental, não a regra de ordenação atual.

## Execução

```bash
python -m pip install -r score/requirements.txt

python score/apply_idade_mortality_multiplier.py
python score/apply_comorbidity_multiplier.py
```

Os comandos leem `data/fila_cirurgica.csv` e produzem, respectivamente:

```text
data/processed/pacientes_com_multiplicador_idade_mortalidade.parquet
data/processed/pacientes_com_multiplicador_idade_mortalidade.csv
data/processed/pacientes_com_multiplicador_comorbidade.parquet
data/processed/pacientes_com_multiplicador_comorbidade.csv
```

Consultar apenas um paciente:

```bash
python score/apply_idade_mortality_multiplier.py --patient-id PAC-00348
python score/apply_comorbidity_multiplier.py --patient-id PAC-00177
```

Se houver mais de uma solicitação para o mesmo `paciente_id`, o módulo devolve
uma linha por solicitação.

## Documentação detalhada

- [Como é calculado o multiplicador de comorbidade](understand_comorbidity_multiplier.md)
- [Como é calculado o multiplicador de idade e mortalidade](understand_idade_mortality_multiplier.md)
- [Decisões metodológicas e de implementação](decisoes.md)

## Limites

- Nenhum multiplicador é uma probabilidade individual de óbito.
- Ausência de evidência não reduz o score: o fator neutro é `1,00`.
- Os fatores não substituem a avaliação do regulador ou as camadas de segurança
  da fila.
