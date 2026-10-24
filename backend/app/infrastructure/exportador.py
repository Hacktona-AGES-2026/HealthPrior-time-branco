"""Escrita do fila_priorizada.csv (US-09). Colunas obrigatórias primeiro."""
from __future__ import annotations

import csv
from pathlib import Path

COLUNAS_OBRIGATORIAS = ["solicitacao_id", "posicao", "justificativa"]


class ExportadorCsv:
    def exportar(self, linhas: list[dict], caminho: Path) -> Path:
        """`linhas` são dicts com pelo menos as colunas obrigatórias; extras viram colunas a mais."""
        caminho.parent.mkdir(parents=True, exist_ok=True)
        extras = [c for c in (linhas[0].keys() if linhas else []) if c not in COLUNAS_OBRIGATORIAS]
        with caminho.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUNAS_OBRIGATORIAS + extras)
            w.writeheader()
            w.writerows(linhas)
        return caminho
