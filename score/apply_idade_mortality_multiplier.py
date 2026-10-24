#!/usr/bin/env python3
"""Resolve the bounded age-and-mortality-context multiplier for queue patients.

The module is intentionally separate from the score. It enriches a patient
with the historical IRR and returns a multiplier for a later score join; it
does not overwrite the queue or reorder patients.

Formula approved for the hackathon context:
    multiplier = 1.00                         if IRR is null, 0, or <= 1
    multiplier = 1 + 0.075 * min(log2(IRR), 2) if IRR > 1

The maximum multiplier is therefore 1.15.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent
DEFAULT_QUEUE = PROJECT_DIR / "data" / "fila_cirurgica.csv"
DEFAULT_IRR = MODULE_DIR / "references" / "irr_nacional_cid_idade_2019_2023.parquet"
DEFAULT_OUTPUT = PROJECT_DIR / "data" / "processed" / "pacientes_com_multiplicador_idade_mortalidade.parquet"


def normalize_cid(value: object) -> str | None:
    """Normalize C50.4 to the CID-3 key C50."""
    import re

    cleaned = re.sub(r"[^A-Z0-9]", "", str(value).upper())
    match = re.match(r"^([A-Z][0-9]{2})", cleaned)
    return match.group(1) if match else None


def age_band(age: object) -> str | None:
    """Map completed age in years to the mortality-table age bands."""
    try:
        numeric_age = int(float(age))
    except (TypeError, ValueError):
        return None
    if numeric_age < 0:
        return None
    if numeric_age <= 17:
        return "0-17"
    if numeric_age <= 39:
        return "18-39"
    if numeric_age <= 49:
        return "40-49"
    if numeric_age <= 59:
        return "50-59"
    if numeric_age <= 69:
        return "60-69"
    if numeric_age <= 79:
        return "70-79"
    return "80+"


def idade_mortality_multiplier(irr: object) -> tuple[float, str]:
    """Return the bounded multiplier and its audit rule for one IRR.

    A null IRR means the CID has no valid historical reference. An IRR of zero
    means no observed deaths in the age cell. Neither case reduces a patient's
    score; both intentionally receive the neutral multiplier 1.00.
    """
    try:
        numeric_irr = float(irr)
    except (TypeError, ValueError):
        return 1.0, "neutro_irr_indisponivel"
    if not math.isfinite(numeric_irr):
        return 1.0, "neutro_irr_indisponivel"
    if numeric_irr <= 0:
        return 1.0, "neutro_sem_obito_na_celula"
    if numeric_irr <= 1:
        return 1.0, "neutro_irr_ate_1"
    multiplier = 1 + 0.075 * min(math.log2(numeric_irr), 2)
    return min(multiplier, 1.15), "ajuste_log2_irr_limitado_em_1_15"


def enrich_patients(patients: pd.DataFrame, irr_table: pd.DataFrame) -> pd.DataFrame:
    """Attach IRR and multiplier to a table with patient_id, cid_principal and idade."""
    required_patients = {"paciente_id", "cid_principal", "idade"}
    required_irr = {
        "cid_3",
        "faixa_idade",
        "irr_contextual",
        "nivel_contexto",
        "motivo_indisponibilidade",
    }
    missing_patients = required_patients - set(patients.columns)
    missing_irr = required_irr - set(irr_table.columns)
    if missing_patients:
        raise ValueError(f"Base de pacientes sem colunas: {sorted(missing_patients)}")
    if missing_irr:
        raise ValueError(f"Tabela de IRR sem colunas: {sorted(missing_irr)}")

    result = patients.copy()
    result["cid_3"] = result["cid_principal"].map(normalize_cid)
    result["faixa_idade"] = result["idade"].map(age_band)
    lookup_columns = [
        "cid_3",
        "faixa_idade",
        "irr_contextual",
        "nivel_contexto",
        "motivo_indisponibilidade",
    ]
    result = result.merge(irr_table[lookup_columns], on=["cid_3", "faixa_idade"], how="left")
    invalid_key = result["cid_3"].isna() | result["faixa_idade"].isna()
    result.loc[invalid_key, "motivo_indisponibilidade"] = "cid_ou_idade_invalido"

    resolved = result["irr_contextual"].map(idade_mortality_multiplier)
    result["multiplicador_idade_mortalidade"] = resolved.map(lambda value: value[0])
    result["regra_multiplicador_idade_mortalidade"] = resolved.map(lambda value: value[1])
    result["descricao_multiplicador_idade_mortalidade"] = result.apply(
        describe_multiplier, axis=1
    )
    return result


def describe_multiplier(row: pd.Series) -> str:
    irr = row.get("irr_contextual")
    multiplier = row["multiplicador_idade_mortalidade"]
    if pd.isna(irr):
        reason = row.get("motivo_indisponibilidade") or "sem_referencia"
        return (
            "Multiplicador de idade e mortalidade 1,00 (neutro): "
            f"IRR indisponível ({reason})."
        )
    return (
        f"IRR histórico de {float(irr):.2f}; "
        f"multiplicador de idade e mortalidade aplicado: {multiplier:.3f}."
    )


def apply_to_score(patients: pd.DataFrame, score_column: str) -> pd.DataFrame:
    """Optionally calculate a capped 0--100 score without changing the base score."""
    if score_column not in patients.columns:
        raise ValueError(f"Coluna de score inexistente: {score_column}")
    result = patients.copy()
    base = pd.to_numeric(result[score_column], errors="coerce")
    result["score_base_idade_mortalidade_contextual"] = base
    result["score_com_contexto_idade_mortalidade"] = (
        base * result["multiplicador_idade_mortalidade"]
    ).clip(upper=100)
    return result


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    raise ValueError(f"Formato não suportado: {path}. Use CSV ou Parquet.")


def write_table(frame: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".parquet":
        frame.to_parquet(output, index=False)
        frame.to_csv(output.with_suffix(".csv"), index=False)
        return
    if output.suffix.lower() == ".csv":
        frame.to_csv(output, index=False)
        return
    raise ValueError(f"Formato de saída não suportado: {output}. Use CSV ou Parquet.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patients", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--irr-table", type=Path, default=DEFAULT_IRR)
    parser.add_argument("--patient-id", help="Mostra somente este paciente no terminal.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Saída quando --patient-id não for informado.",
    )
    parser.add_argument(
        "--score-column",
        help="Opcional: coluna 0--100 a multiplicar; preserva a coluna original.",
    )
    args = parser.parse_args()

    patients = read_table(args.patients)
    irr_table = read_table(args.irr_table)
    result = enrich_patients(patients, irr_table)
    if args.score_column:
        result = apply_to_score(result, args.score_column)

    if args.patient_id:
        selected = result.loc[result["paciente_id"].astype(str).eq(args.patient_id)]
        if selected.empty:
            raise SystemExit(f"paciente_id não encontrado: {args.patient_id}")
        columns = [
            "paciente_id",
            "cid_principal",
            "idade",
            "cid_3",
            "faixa_idade",
            "irr_contextual",
            "multiplicador_idade_mortalidade",
            "regra_multiplicador_idade_mortalidade",
            "motivo_indisponibilidade",
            "descricao_multiplicador_idade_mortalidade",
        ]
        print(selected[columns].to_json(orient="records", force_ascii=False, indent=2))
        return

    write_table(result, args.output)
    print(f"Pacientes processados: {len(result)}")
    print(f"Saída: {args.output}")


if __name__ == "__main__":
    main()
