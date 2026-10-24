"""US-19 · SWALIS + regras aprendidas aprovadas pelo comitê (C-14, "volta ao SWALIS").

Decora o `SwalisScorer`: calcula como sempre e, se uma regra aprovada bate (procedimento + classe_de),
troca a classe sugerida e refaz prazo e % do prazo. A fórmula do tempo não muda; só a classe.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.domain.enums import PRAZO_MAXIMO_DIAS
from app.domain.models import Evento, Motivo, ResultadoScore, Solicitacao
from app.domain.regras_aprendidas import RegraAprendida, aplicar_regras, versao_atual


class SwalisComRegras:
    def __init__(self, base, regras: list[RegraAprendida], ref_date: date | None = None):
        self._base = base
        self.regras = regras
        self._ref = ref_date or getattr(base, "_ref", None) or settings.ref_date
        v = versao_atual(regras)
        self.versao_regras = base.versao_regras + (f"+aprendizado-v{v}" if v else "")

    def __getattr__(self, nome):  # classificar, sinais, pontos_llm... seguem do SWALIS base
        return getattr(self._base, nome)

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore:
        r = self._base.calcular(solicitacao, eventos)
        nova, regra = aplicar_regras(solicitacao, r.classe_sistema, self.regras)
        if regra is None:
            return ResultadoScore(r.classe_sistema, r.prazo_dias, r.pct_prazo_consumido,
                                  r.score_sistema, r.motivos, self.versao_regras, r.fator_contexto)
        prazo = PRAZO_MAXIMO_DIAS[nova]
        pct = round(100 * (self._ref - solicitacao.data_entrada_fila).days / prazo, 1)
        motivos = list(r.motivos) + [Motivo(
            "regra_aprendida", f"{regra.classe_de.value} → {regra.classe_para.value} para este "
            f"procedimento (aprovada pelo comitê, v{regra.versao})", "regra", ref=regra.regra_id)]
        return ResultadoScore(nova, prazo, pct, round(pct * r.fator_contexto, 1), motivos,
                              self.versao_regras, r.fator_contexto)


def com_regras(base, session, ref_date: date | None = None):
    """Embrulha o SWALIS com as regras ativas do banco; sem a tabela ou sem regras, devolve o próprio."""
    from app.infrastructure.repositories import SqlRegraRepository

    try:
        regras = SqlRegraRepository(session).listar_ativas()
    except SQLAlchemyError:
        session.rollback()
        return base
    return SwalisComRegras(base, regras, ref_date) if regras else base
