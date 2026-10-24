"""PRE-10..PRE-25 (US-04, US-05): detecção de inconsistências.

Cada regra devolve uma lista de Achado. Nada é apagado (I-03).
Oncológico nunca é suspenso sem confirmação humana (I-02).
"""
from __future__ import annotations

from app.domain.models import Achado, Evento, Solicitacao


def detectar_bloqueantes(
    solicitacao: Solicitacao,
    eventos: list[Evento],
    outras_do_paciente: list[Solicitacao],
) -> list[Achado]:
    """TODO(US-04): PRE-20 duplicata, PRE-21/22 operou fora, PRE-23 desistência,
    PRE-24 evento órfão, PRE-25 fontes contraditórias."""
    raise NotImplementedError("US-04: detectar_bloqueantes")


def detectar_nao_bloqueantes(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Achado]:
    """TODO(US-05): PRE-10..PRE-15 (contato perdido, câncer escondido, cadastro, texto vazio)."""
    raise NotImplementedError("US-05: detectar_nao_bloqueantes")
