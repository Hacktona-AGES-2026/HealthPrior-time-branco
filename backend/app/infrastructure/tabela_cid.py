"""Tabela CID-10 do DATASUS (`data/referencias/CID10CSV`), para buscar e validar códigos (PRE-12)."""
from __future__ import annotations

import csv
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.domain.cid import normalizar_cid


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _com_ponto(codigo: str) -> str:
    return f"{codigo[:3]}.{codigo[3:]}" if len(codigo) > 3 else codigo


class TabelaCidDatasus:
    """Subcategorias (ex.: C50.9) e categorias sem subdivisão (ex.: C73) do CID-10."""

    def __init__(self, data_dir: Path):
        pasta = data_dir / "referencias" / "CID10CSV"
        self._descricoes: dict[str, str] = {}
        for arquivo, coluna in (("CID-10-CATEGORIAS.CSV", "CAT"), ("CID-10-SUBCATEGORIAS.CSV", "SUBCAT")):
            with (pasta / arquivo).open(encoding="latin1", newline="") as f:
                for linha in csv.DictReader(f, delimiter=";"):
                    self._descricoes[normalizar_cid(linha[coluna])] = linha["DESCRICAO"].strip()
        # Busca só em códigos "folha": a categoria que tem subcategorias fica de fora (C50 -> C50.0..C50.9).
        com_filhos = {c[:3] for c in self._descricoes if len(c) > 3}
        self._busca = [(_com_ponto(c), d, _sem_acento(d)) for c, d in sorted(self._descricoes.items())
                       if len(c) > 3 or c not in com_filhos]

    def descricao(self, cid: str) -> str | None:
        return self._descricoes.get(normalizar_cid(cid))

    def buscar(self, consulta: str, limite: int = 12) -> list[tuple[str, str]]:
        termos = [t for t in _sem_acento(consulta).replace(",", " ").split() if len(t) > 2]
        if not termos:
            return []
        pontuados = sorted(((sum(t in d for t in termos), c, desc) for c, desc, d in self._busca),
                           key=lambda x: (-x[0], x[1]))
        return [(c, desc) for pontos, c, desc in pontuados[:limite] if pontos > 0]


@lru_cache(maxsize=4)
def tabela_cid(data_dir: Path) -> TabelaCidDatasus:
    """Lida uma vez por processo: são ~14 mil linhas."""
    return TabelaCidDatasus(data_dir)
