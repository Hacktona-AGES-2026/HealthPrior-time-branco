"""Importação de solicitações por CSV: o que a leitura devolve (sem I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ErroLinha:
    linha: int  # 1 = cabeçalho; os dados começam na 2
    campo: str | None
    mensagem: str


@dataclass
class LeituraCsv:
    registros: list[dict] = field(default_factory=list)
    erros: list[ErroLinha] = field(default_factory=list)
    lidas: int = 0  # linhas de dados (sem contar vazias)
