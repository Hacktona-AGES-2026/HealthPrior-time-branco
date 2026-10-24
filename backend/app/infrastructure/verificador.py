"""Adaptador do verificador oficial (src/verificar_fila_priorizada.py). Portão de publicação (I-07)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.config import settings


class VerificadorOficial:
    def __init__(self, script: Path | None = None, data_dir: Path | None = None):
        self._script = script or settings.verificador_path
        self._data_dir = data_dir or settings.data_dir

    def verificar(self, caminho_csv: Path) -> tuple[bool, str]:
        proc = subprocess.run(
            [sys.executable, str(self._script), str(caminho_csv), "--dataset", str(self._data_dir)],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stdout + proc.stderr
