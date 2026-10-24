"""US-12 · Regras do inbox do regulador (puras).

Um paciente entra no inbox quando a classe sugerida pelo SWALIS merece revisão humana:
- nunca confirmado: diverge 2 ou mais níveis da classe implícita da prioridade manual;
- já confirmado: a sugerida difere da classe confirmada.
"""
from __future__ import annotations

from app.domain.enums import Classe, ClasseStatus

ORDEM_CLASSES: list[Classe] = [Classe.A1, Classe.A2, Classe.B, Classe.C, Classe.D]
DISTANCIA_MINIMA_NAO_CONFIRMADO = 2

_IMPLICITA = {"alta": Classe.B, "media": Classe.C, "baixa": Classe.D}


def classe_implicita_prioridade(prioridade_norm: str | None) -> Classe:
    """alta->B, media->C, baixa->D; vazia ou desconhecida->D."""
    return _IMPLICITA.get((prioridade_norm or "").strip().lower(), Classe.D)


def distancia(a: Classe, b: Classe) -> int:
    return abs(ORDEM_CLASSES.index(a) - ORDEM_CLASSES.index(b))


def classe_referencia(classe_status: ClasseStatus, classe_confirmada: Classe | None,
                      prioridade_norm: str | None) -> Classe:
    """Classe atual do paciente: a confirmada, se houver; senão a implícita da prioridade."""
    if classe_status == ClasseStatus.CONFIRMADA and classe_confirmada is not None:
        return classe_confirmada
    return classe_implicita_prioridade(prioridade_norm)


def entra_no_inbox(sugerida: Classe, classe_status: ClasseStatus,
                   classe_confirmada: Classe | None, prioridade_norm: str | None) -> bool:
    referencia = classe_referencia(classe_status, classe_confirmada, prioridade_norm)
    if classe_status == ClasseStatus.CONFIRMADA and classe_confirmada is not None:
        return sugerida != referencia
    return distancia(sugerida, referencia) >= DISTANCIA_MINIMA_NAO_CONFIRMADO


def chave_ordenacao(sugerida: Classe, dist: int, posicao: int) -> tuple[int, int, int]:
    """Mais grave primeiro (A1>...>D), maior distância, menor posição publicada."""
    return (ORDEM_CLASSES.index(sugerida), -dist, posicao)
