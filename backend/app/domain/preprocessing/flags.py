"""PRE-05..PRE-08 (US-03): flags recalculadas e eventos limpos."""
from __future__ import annotations

from app.domain.models import Correcao, Evento, Solicitacao


def recalcular_flags(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Correcao]:
    """TODO(US-03): oncologico pelo CID (PRE-05), piora pelos eventos (PRE-06).

    Atualiza a solicitação e devolve as correções feitas (I-10).
    """
    raise NotImplementedError("US-03: recalcular_flags")


def marcar_eventos(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Evento]:
    """TODO(US-03): marca duplicados (PRE-07) e histórico anterior à entrada (PRE-08)."""
    raise NotImplementedError("US-03: marcar_eventos")
