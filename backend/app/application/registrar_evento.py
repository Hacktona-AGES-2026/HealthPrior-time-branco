"""US-15 · Registrar evento novo (C-03, C-08).

Evento -> pré-processamento -> SWALIS -> se a classe mudou, vai ao inbox; senão, só registra (D-02).
"""
from __future__ import annotations

from app.domain.enums import DesfechoEvento
from app.domain.models import Evento


class RegistrarEvento:
    def __init__(self, solicitacoes, eventos, scorer, pendencias):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._scorer = scorer
        self._pendencias = pendencias

    def executar(self, evento: Evento) -> DesfechoEvento:
        """TODO(US-15)."""
        raise NotImplementedError("US-15: RegistrarEvento.executar")
