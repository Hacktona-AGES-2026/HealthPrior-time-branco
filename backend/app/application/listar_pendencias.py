"""US-06 · Lista de pendências (C-06).

A lista de trabalho do administrativo: pendências com motivo, evidência de origem e ação sugerida.
Só leitura. Por padrão mostra as abertas; os filtros são `bloqueante`, `regra` e `status`.
"""
from __future__ import annotations

from app.domain.enums import StatusPendencia
from app.domain.models import Pendencia
from app.domain.ports import PendenciaRepository


class ListarPendencias:
    def __init__(self, pendencias: PendenciaRepository):
        self._pendencias = pendencias

    def executar(self, bloqueante: bool | None = None, regra: str | None = None,
                 status: StatusPendencia = StatusPendencia.ABERTA) -> list[Pendencia]:
        return self._pendencias.listar(bloqueante=bloqueante, regra=regra, status=status.value)
