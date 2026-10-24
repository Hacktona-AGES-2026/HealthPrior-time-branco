"""Carga inicial dos CSVs no Postgres (US-01).

Idempotente: cada linha entra por upsert na chave primária. Uma recarga atualiza só as
colunas do CSV e preserva o estado do sistema (classe_status, status_fila).
"""
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import Date, Engine, Integer, Numeric, literal_column
from sqlalchemy.dialects.postgresql import insert

from app.models import Base, Evento, Procedimento, Solicitacao
from app.normalization import NormalizacaoResult, normalizar

CHUNK_SIZE = 500

# Ordem importa: solicitacoes referencia procedimentos.
SOURCES = [
    ("procedimentos", "procedimentos.csv", Procedimento),
    ("solicitacoes", "fila_cirurgica.csv", Solicitacao),
    ("eventos", "eventos_clinicos.csv", Evento),
]


class CargaError(Exception):
    """Problema nos arquivos de entrada (ausente, colunas ou chaves inesperadas)."""


@dataclass
class TableResult:
    lido: int = 0
    inseridos: int = 0
    atualizados: int = 0


@dataclass
class CargaResult:
    tabelas: Dict[str, TableResult]
    normalizacao: NormalizacaoResult


def _csv_columns(model: type) -> List[str]:
    """Colunas da tabela que vêm do CSV (as de estado do sistema ficam de fora)."""
    return [c.name for c in model.__table__.columns if not c.info.get("sistema")]


def _coerce(column, raw: str) -> Any:
    if raw == "":
        return None
    t = column.type
    if isinstance(t, Integer):
        return int(raw)
    if isinstance(t, Date):
        return date.fromisoformat(raw)
    if isinstance(t, Numeric):
        return Decimal(raw)
    return raw


def read_rows(path: Path, model: type) -> List[Dict[str, Any]]:
    if not path.is_file():
        raise CargaError(f"Arquivo não encontrado: {path}")
    columns = _csv_columns(model)
    pk = model.__table__.primary_key.columns.keys()[0]
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            raise CargaError(
                f"{path.name}: colunas inesperadas.\n  esperado: {columns}\n  lido: {reader.fieldnames}"
            )
        table_cols = model.__table__.columns
        rows = []
        for n, raw in enumerate(reader, start=2):
            try:
                rows.append({c: _coerce(table_cols[c], raw[c]) for c in columns})
            except ValueError as e:
                raise CargaError(f"{path.name} linha {n}: valor inválido ({e})") from e
    ids = [r[pk] for r in rows]
    if len(set(ids)) != len(ids):
        raise CargaError(f"{path.name}: {pk} repetido no arquivo")
    return rows


def _upsert(conn, model: type, rows: List[Dict[str, Any]]) -> TableResult:
    result = TableResult(lido=len(rows))
    pk = model.__table__.primary_key.columns.keys()[0]
    for i in range(0, len(rows), CHUNK_SIZE):
        stmt = insert(model).values(rows[i : i + CHUNK_SIZE])
        stmt = stmt.on_conflict_do_update(
            index_elements=[pk],
            set_={c: stmt.excluded[c] for c in rows[0] if c != pk},
        ).returning(literal_column("xmax = 0"))  # true = linha nova, false = atualizada
        flags = [r[0] for r in conn.execute(stmt)]
        result.inseridos += sum(flags)
        result.atualizados += len(flags) - sum(flags)
    return result


def carga(engine: Engine, data_dir: Path) -> CargaResult:
    """Carrega os três CSVs e normaliza (US-02) numa única transação: ou entra tudo, ou nada."""
    Base.metadata.create_all(engine)
    parsed = [(name, model, read_rows(data_dir / filename, model)) for name, filename, model in SOURCES]
    with engine.begin() as conn:
        tabelas = {name: _upsert(conn, model, rows) for name, model, rows in parsed}
        return CargaResult(tabelas=tabelas, normalizacao=normalizar(conn))
