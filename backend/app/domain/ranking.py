"""Trava da regra de ouro (C-11, US-08). Função pura: recebe itens, devolve a fila ordenada.

Regras (docs/fluxo-sistema.md C-11):
- Camada 1: oncológicos (CID C*).
- Camada 2: urgentes não oncológicos.
- Camada 3: demais.
- Dentro da camada: score_efetivo decrescente; desempate por data de entrada mais antiga.
- Nenhuma camada invade a de cima (I-01).
"""
from __future__ import annotations

from app.domain.enums import Camada
from app.domain.models import ItemFila, ItemRanking


def definir_camada(item: ItemRanking) -> Camada:
    """TODO(US-08): implementar."""
    raise NotImplementedError("US-08: definir_camada")


def ordenar_fila(itens: list[ItemRanking]) -> list[ItemFila]:
    """TODO(US-08): implementar. Deve devolver posições 1..n sem buracos."""
    raise NotImplementedError("US-08: ordenar_fila")
