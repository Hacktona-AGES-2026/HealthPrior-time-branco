"""Leitura do dataset oficial (data/). Só leitura; nunca escreve nos CSVs."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import Date, Float, Integer

from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.tables import EventoTable, ProcedimentoTable, SolicitacaoTable

# Última coluna que vem do CSV; as seguintes são normalizadas/estado do sistema e não são lidas.
_ULTIMA_ORIGINAL = {
    ProcedimentoTable: "necessita_uti",
    SolicitacaoTable: "exames_pre_op_validos",
    EventoTable: "origem",
}


def _colunas_originais(tabela: type) -> list[str]:
    nomes = [c.name for c in tabela.__table__.columns]
    return nomes[: nomes.index(_ULTIMA_ORIGINAL[tabela]) + 1]


def _converter(coluna, bruto: str) -> Any:
    """Vazio vira None; o resto mantém o valor do CSV (só muda o tipo)."""
    if bruto == "":
        return None
    tipo = coluna.type
    if isinstance(tipo, Integer):
        return int(bruto)
    if isinstance(tipo, Float):
        return float(bruto)
    if isinstance(tipo, Date):
        return date.fromisoformat(bruto)
    return bruto


class LeitorDataset:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.data_dir

    def procedimentos(self) -> list[dict]:
        return self._registros("procedimentos.csv", ProcedimentoTable)

    def fila(self) -> list[dict]:
        return self._registros("fila_cirurgica.csv", SolicitacaoTable)

    def eventos(self) -> list[dict]:
        return self._registros("eventos_clinicos.csv", EventoTable)

    def swalis(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "referencias" / "swalis.csv")

    def _registros(self, arquivo: str, tabela: type) -> list[dict]:
        caminho = self.data_dir / arquivo
        if not caminho.is_file():
            raise CargaInvalidaError(f"Arquivo não encontrado: {caminho}")
        esperadas = _colunas_originais(tabela)
        colunas = tabela.__table__.columns
        pk = tabela.__table__.primary_key.columns.keys()[0]
        with caminho.open(encoding="utf-8", newline="") as f:
            leitor = csv.DictReader(f)
            if leitor.fieldnames != esperadas:
                raise CargaInvalidaError(
                    f"{arquivo}: colunas inesperadas.\n  esperado: {esperadas}\n  lido: {leitor.fieldnames}"
                )
            registros = []
            for n, linha in enumerate(leitor, start=2):
                try:
                    registros.append({c: _converter(colunas[c], linha[c]) for c in esperadas})
                except ValueError as e:
                    raise CargaInvalidaError(f"{arquivo} linha {n}: valor inválido ({e})") from e
        ids = [r[pk] for r in registros]
        if len(set(ids)) != len(ids):
            raise CargaInvalidaError(f"{arquivo}: {pk} repetido no arquivo")
        return registros
