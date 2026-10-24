"""Adaptador do verificador oficial (src/verificar_fila_priorizada.py). Portão de publicação (I-07)."""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import select

from app.config import settings


class VerificadorOficial:
    """Roda o script oficial. Com `session`, solicitações que não estão no `fila_cirurgica.csv` oficial (as
    importadas por CSV) entram numa cópia temporária do dataset, para o verificador as conhecer.
    O script e os CSVs oficiais nunca são alterados.
    """

    def __init__(self, script: Path | None = None, data_dir: Path | None = None, session=None):
        self._script = script or settings.verificador_path
        self._data_dir = data_dir or settings.data_dir
        self._session = session

    def verificar(self, caminho_csv: Path) -> tuple[bool, str]:
        extras = self._importadas()
        if not extras:
            return self._rodar(caminho_csv, self._data_dir)
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp)
            for nome in ("eventos_clinicos.csv", "procedimentos.csv"):
                if (self._data_dir / nome).is_file():
                    shutil.copyfile(self._data_dir / nome, destino / nome)
            with (self._data_dir / "fila_cirurgica.csv").open(encoding="utf-8", newline="") as f:
                oficial = list(csv.DictReader(f))
            with (destino / "fila_cirurgica.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(oficial[0].keys()))
                w.writeheader()
                w.writerows(oficial + extras)
            return self._rodar(caminho_csv, destino)

    def _rodar(self, caminho_csv: Path, dataset: Path) -> tuple[bool, str]:
        proc = subprocess.run(
            [sys.executable, str(self._script), str(caminho_csv), "--dataset", str(dataset)],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stdout + proc.stderr

    def _importadas(self) -> list[dict]:
        """Linhas (como no CSV oficial) das solicitações do banco que não estão no arquivo oficial."""
        if self._session is None:
            return []
        from app.infrastructure.csv_loader import _colunas_originais
        from app.infrastructure.tables import SolicitacaoTable

        with (self._data_dir / "fila_cirurgica.csv").open(encoding="utf-8", newline="") as f:
            oficiais = {r["solicitacao_id"] for r in csv.DictReader(f)}
        colunas = _colunas_originais(SolicitacaoTable)
        linhas = self._session.execute(
            select(SolicitacaoTable).where(SolicitacaoTable.solicitacao_id.not_in(oficiais))).scalars().all()
        return [{c: "" if getattr(t, c) is None else str(getattr(t, c)) for c in colunas} for t in linhas]
