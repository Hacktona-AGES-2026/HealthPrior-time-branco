"""Tabela nacional de IRR (SIM 2019–2023 / IBGE) por CID-3 × faixa etária, lida do CSV versionado.

O CSV é a exportação de `score/references/irr_nacional_cid_idade_2019_2023.parquet` (mesmas
colunas), para o backend não depender de pyarrow.
"""
from __future__ import annotations

import csv
from pathlib import Path

from app.domain.fatores import CelulaIrr


class TabelaIrrCsv:
    def __init__(self, caminho: Path):
        self._celulas: dict[tuple[str, str], CelulaIrr] = {}
        with caminho.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                irr = r.get("irr_contextual") or ""
                self._celulas[(r["cid_3"], r["faixa_idade"])] = CelulaIrr(
                    irr=float(irr) if irr else None, obitos=int(float(r.get("obitos") or 0)))

    def consultar(self, cid_3: str, faixa_idade: str) -> CelulaIrr | None:
        return self._celulas.get((cid_3, faixa_idade))
