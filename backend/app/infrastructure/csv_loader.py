"""Leitura do dataset oficial (data/). Só leitura; nunca escreve nos CSVs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import settings


class LeitorDataset:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.data_dir

    def fila(self) -> pd.DataFrame:
        return pd.read_csv(
            self.data_dir / "fila_cirurgica.csv",
            parse_dates=["data_entrada_fila", "data_ultima_revisao_prioridade", "data_hba1c_ultima"],
            dtype={"cid_principal": str, "cid_secundario": str},
        )

    def eventos(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "eventos_clinicos.csv", parse_dates=["data_evento"])

    def procedimentos(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "procedimentos.csv")

    def swalis(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "referencias" / "swalis.csv")
