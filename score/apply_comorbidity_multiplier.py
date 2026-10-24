#!/usr/bin/env python3
"""Resolve a bounded comorbidity multiplier using Charlson without age.

The score intentionally excludes `idade` and `cid_principal`:
age already belongs to the mortality-context IRR, while the principal CID is
usually the condition that motivated the procedure, not a comorbidity.

Charlson (without age) -> multiplier
0 -> 1.00 | 1 -> 1.03 | 2 -> 1.06 | 3-4 -> 1.10 | 5+ -> 1.15
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent
DEFAULT_PATIENTS = PROJECT_DIR / "data" / "fila_cirurgica.csv"
DEFAULT_OUTPUT = PROJECT_DIR / "data" / "processed" / "pacientes_com_multiplicador_comorbidade.parquet"

# Charlson categories supported by this dataset and their published point value.
CHARLSON_WEIGHTS = {
    "infarto_miocardio": 1,
    "insuficiencia_cardiaca": 1,
    "doenca_pulmonar_cronica": 1,
    "diabetes_sem_complicacao": 1,
    "doenca_renal": 2,
    "tumor_solido": 2,
    "linfoma_leucemia": 2,
    "metastatico": 6,
}

TEXT_TO_CHARLSON = {
    "icc": "insuficiencia_cardiaca",
    "insuficiencia cardiaca": "insuficiencia_cardiaca",
    "cardiopatia isquemica": "infarto_miocardio",
    "infarto": "infarto_miocardio",
    "dpoc": "doenca_pulmonar_cronica",
    "asma": "doenca_pulmonar_cronica",
    "drc": "doenca_renal",
    "doenca renal cronica": "doenca_renal",
    "dm2": "diabetes_sem_complicacao",
    "diabetes": "diabetes_sem_complicacao",
}

METASTATIC_CODES = ("C77", "C78", "C79", "C80")
LYMPHOMA_LEUKEMIA_CODES = (
    "C81", "C82", "C83", "C84", "C85", "C88", "C90", "C91", "C92", "C93",
    "C94", "C95", "C96",
)


def normalize_cid(value: object) -> str | None:
    cleaned = re.sub(r"[^A-Z0-9]", "", str(value).upper())
    match = re.match(r"^([A-Z][0-9]{2})", cleaned)
    return match.group(1) if match else None


def charlson_from_secondary_cid(value: object) -> str | None:
    """Map only a *secondary* CID to the supported Charlson category."""
    cid = normalize_cid(value)
    if cid is None:
        return None
    if cid in METASTATIC_CODES:
        return "metastatico"
    if cid in LYMPHOMA_LEUKEMIA_CODES:
        return "linfoma_leucemia"
    if cid.startswith("C"):
        return "tumor_solido"
    if cid == "I50":
        return "insuficiencia_cardiaca"
    if cid in {"I21", "I22", "I25"}:
        return "infarto_miocardio"
    if cid in {"J44", "J45"}:
        return "doenca_pulmonar_cronica"
    if cid == "N18":
        return "doenca_renal"
    if cid[0] == "E" and cid[1:3].isdigit() and 10 <= int(cid[1:3]) <= 14:
        return "diabetes_sem_complicacao"
    return None


def extract_charlson(row: pd.Series) -> tuple[set[str], list[str]]:
    """Extract unique scoreable categories and their source for auditability."""
    categories: set[str] = set()
    sources: list[str] = []

    text = str(row.get("comorbidades", "")) if pd.notna(row.get("comorbidades")) else ""
    for term in (item.strip().lower() for item in text.split(";")):
        category = TEXT_TO_CHARLSON.get(term)
        if category:
            categories.add(category)
            sources.append(f"texto:{term}")

    secondary = str(row.get("cid_secundario", "")) if pd.notna(row.get("cid_secundario")) else ""
    for raw_cid in re.split(r"[;,\s]+", secondary):
        category = charlson_from_secondary_cid(raw_cid)
        if category:
            categories.add(category)
            sources.append(f"cid_secundario:{normalize_cid(raw_cid)}")

    return categories, sorted(set(sources))


def comorbidity_multiplier(charlson_without_age: int) -> tuple[float, str]:
    if charlson_without_age <= 0:
        return 1.00, "charlson_0"
    if charlson_without_age == 1:
        return 1.03, "charlson_1"
    if charlson_without_age == 2:
        return 1.06, "charlson_2"
    if charlson_without_age <= 4:
        return 1.10, "charlson_3_a_4"
    return 1.15, "charlson_5_ou_mais"


def enrich_patients(patients: pd.DataFrame) -> pd.DataFrame:
    """Attach Charlson-without-age and the bounded multiplier to each request."""
    required = {"solicitacao_id", "paciente_id", "comorbidades", "cid_secundario"}
    missing = required - set(patients.columns)
    if missing:
        raise ValueError(f"Base de pacientes sem colunas: {sorted(missing)}")

    result = patients.copy()
    extracted = result.apply(extract_charlson, axis=1)
    result["categorias_charlson_comorbidade"] = extracted.map(
        lambda item: ", ".join(sorted(item[0])) or "nenhuma"
    )
    result["fontes_categorias_charlson"] = extracted.map(
        lambda item: ", ".join(item[1]) or "nenhuma"
    )
    result["charlson_sem_idade"] = extracted.map(
        lambda item: sum(CHARLSON_WEIGHTS[category] for category in item[0])
    )
    multiplier = result["charlson_sem_idade"].map(comorbidity_multiplier)
    result["multiplicador_comorbidade"] = multiplier.map(lambda item: item[0])
    result["regra_multiplicador_comorbidade"] = multiplier.map(lambda item: item[1])
    result["descricao_multiplicador_comorbidade"] = result.apply(
        lambda row: (
            f"Charlson sem idade: {row['charlson_sem_idade']}; "
            f"multiplicador de comorbidade aplicado: {row['multiplicador_comorbidade']:.2f}."
        ),
        axis=1,
    )
    return result


def apply_to_score(patients: pd.DataFrame, score_column: str) -> pd.DataFrame:
    """Optionally apply the factor to a 0--100 score while preserving the base."""
    if score_column not in patients.columns:
        raise ValueError(f"Coluna de score inexistente: {score_column}")
    result = patients.copy()
    base = pd.to_numeric(result[score_column], errors="coerce")
    result["score_base_comorbidade"] = base
    result["score_com_comorbidade"] = (
        base * result["multiplicador_comorbidade"]
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
    parser.add_argument("--patients", type=Path, default=DEFAULT_PATIENTS)
    parser.add_argument("--patient-id", help="Mostra somente este paciente no terminal.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--score-column",
        help="Opcional: coluna 0--100 a multiplicar; preserva a coluna original.",
    )
    args = parser.parse_args()

    result = enrich_patients(read_table(args.patients))
    if args.score_column:
        result = apply_to_score(result, args.score_column)

    if args.patient_id:
        selected = result.loc[result["paciente_id"].astype(str).eq(args.patient_id)]
        if selected.empty:
            raise SystemExit(f"paciente_id não encontrado: {args.patient_id}")
        columns = [
            "solicitacao_id",
            "paciente_id",
            "categorias_charlson_comorbidade",
            "fontes_categorias_charlson",
            "charlson_sem_idade",
            "multiplicador_comorbidade",
            "regra_multiplicador_comorbidade",
            "descricao_multiplicador_comorbidade",
        ]
        print(selected[columns].to_json(orient="records", force_ascii=False, indent=2))
        return

    write_table(result, args.output)
    print(f"Solicitações processadas: {len(result)}")
    print(f"Saída: {args.output}")


if __name__ == "__main__":
    main()
