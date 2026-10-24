# AGENTS.md — score

## Stack

- Python 3.12
- `pandas` e `pyarrow`

## Como rodar

```bash
python -m pip install -r score/requirements.txt
python score/apply_idade_mortality_multiplier.py
python score/apply_comorbidity_multiplier.py
```

## Como testar

```bash
python score/apply_idade_mortality_multiplier.py --patient-id PAC-00348
python score/apply_comorbidity_multiplier.py --patient-id PAC-00177
```

## Estrutura

```text
score/
  apply_idade_mortality_multiplier.py fator por CID e faixa etária
  apply_comorbidity_multiplier.py fator Charlson sem idade
  references/                      tabela IRR versionada para consulta
  README.md                        contrato de integração com o score externo
```

## Convenções locais

- Os módulos não ordenam nem modificam a fila; apenas geram fatores auditáveis.
- O CID principal não entra no multiplicador de comorbidade.
- Idade não entra no multiplicador de comorbidade, pois já compõe o IRR de mortalidade.
- O JEV/LLM configurado no projeto permanece alerta explicável e não altera classe ou score sem decisão documentada.
