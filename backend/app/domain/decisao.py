"""Decisão do regulador (C-09/C-10): regras puras. Hoje só `aprovar` (US-13); editar e manter são da US-14."""
from __future__ import annotations

from datetime import datetime

from app.domain.enums import AcaoDecisao, Classe, ClasseStatus
from app.domain.errors import SemPropostaError
from app.domain.inbox import entra_no_inbox
from app.domain.models import Decisao, Solicitacao
from app.domain.enums import StatusFila


def validar_proposta(solicitacao: Solicitacao, sugerida: Classe) -> None:
    """Só se aprova o que o inbox mostraria: solicitação ativa e classe sugerida que merece decisão (D-64)."""
    if solicitacao.status_fila != StatusFila.ATIVA or not entra_no_inbox(
            sugerida, solicitacao.classe_status, solicitacao.classe_confirmada, solicitacao.prioridade_norm):
        raise SemPropostaError(
            f"Não há proposta pendente para {solicitacao.solicitacao_id}: já está confirmada na classe "
            "sugerida, não diverge o bastante da classe atual ou não está ativa na fila.")


def _override_removido(s: Solicitacao) -> str | None:
    """Texto para o log, se a solicitação tinha um override do regulador (`classe_medico`, US-14)."""
    if s.classe_medico is None and s.score_medico is None and not s.editado_manualmente:
        return None
    partes = []
    if s.classe_medico is not None:
        partes.append(f"classe {s.classe_medico.value}")
    if s.score_medico is not None:
        partes.append(f"score {s.score_medico:g}")
    quem = f"editado por {s.editado_por}" if s.editado_por else "editado manualmente"
    quando = f" em {s.editado_em.strftime('%d/%m/%Y')}" if s.editado_em else ""
    return f"Override anterior removido ({', '.join(partes) or 'sem valores'}; {quem}{quando})."


def aprovar(solicitacao: Solicitacao, sugerida: Classe, regulador_id: str, agora: datetime,
            versao_regras: str, decisao_id: str) -> Decisao:
    """Confirma a classe sugerida (D-66) e devolve o registro do log de decisões.

    A solicitação fica `confirmada` na classe sugerida e perde o override anterior, se houver (D-89):
    aprovar a sugestão é escolhê-la no lugar da classe editada, e o log diz o que foi removido.
    A posição nunca é editada (D-03): quem mexe nela é a fila, ao ser recalculada.
    """
    removido = _override_removido(solicitacao)
    solicitacao.classe_status = ClasseStatus.CONFIRMADA
    solicitacao.classe_confirmada = sugerida
    solicitacao.classe_medico = None
    solicitacao.score_medico = None
    solicitacao.editado_manualmente = False
    solicitacao.editado_por = None
    solicitacao.editado_em = None
    return Decisao(
        decisao_id=decisao_id, solicitacao_id=solicitacao.solicitacao_id, regulador_id=regulador_id,
        acao=AcaoDecisao.APROVAR, data=agora, classe_sugerida=sugerida, classe_decidida=sugerida,
        justificativa=removido, versao_regras=versao_regras, procedimento_id=solicitacao.procedimento_id,
    )
