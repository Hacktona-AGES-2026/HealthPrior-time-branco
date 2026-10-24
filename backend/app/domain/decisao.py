"""US-13/14 · Regras da decisão do regulador (C-09, C-10). Funções puras.

- aprovar: confirma a classe sugerida pelo SWALIS; só vale para o que o inbox mostraria (D-98) e
  desfaz o override anterior, de forma explícita: o log diz o que foi removido (D-100).
- editar: override de classe e/ou score; motivo + justificativa obrigatórios.
- manter: recusa a sugestão e fixa a classe atual; motivo + justificativa obrigatórios.
Edita classe/score, nunca posição (D-03).
"""
from __future__ import annotations

import math
from datetime import datetime

from app.domain.cid import is_oncologico
from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, MotivoCodificado, StatusFila
from app.domain.errors import (
    DecisaoInvalidaError,
    JustificativaObrigatoriaError,
    OncologicoRebaixadoError,
    SemPropostaError,
)
from app.domain.inbox import classe_referencia, entra_no_inbox
from app.domain.models import Solicitacao

# Câncer nunca abaixo de B na classe (mesma regra do SWALIS, docs/swalis.md). Na fila, a camada 1
# já garante a regra de ouro; aqui a edição é recusada antes de chegar lá (I-01).
CLASSES_PROIBIDAS_ONCOLOGICO = frozenset({Classe.C, Classe.D})


def validar_decisao(solicitacao: Solicitacao, acao: AcaoDecisao, classe: Classe | None,
                    score: float | None, motivo: MotivoCodificado | None,
                    justificativa: str | None) -> None:
    if acao in (AcaoDecisao.EDITAR, AcaoDecisao.MANTER):
        if motivo is None or not (justificativa or "").strip():
            raise JustificativaObrigatoriaError(
                f"'{acao.value}' exige motivo_codificado e justificativa.")
    if acao == AcaoDecisao.EDITAR:
        if classe is None and score is None:
            raise DecisaoInvalidaError("'editar' exige classe ou score.")
        if score is not None and (not math.isfinite(score) or score < 0):
            raise DecisaoInvalidaError("score precisa ser um número finito e não negativo.")
        if classe in CLASSES_PROIBIDAS_ONCOLOGICO and is_oncologico(solicitacao.cid_principal):
            raise OncologicoRebaixadoError()


def validar_proposta(solicitacao: Solicitacao, sugerida: Classe) -> None:
    """Só se aprova o que o inbox mostraria: solicitação ativa e classe sugerida que merece decisão (D-64, D-98)."""
    s = solicitacao
    if s.status_fila != StatusFila.ATIVA or not entra_no_inbox(
            sugerida, s.classe_status, s.classe_confirmada, s.prioridade_norm, s.classe_vigente):
        raise SemPropostaError(
            f"Não há proposta pendente para {s.solicitacao_id}: já está confirmada na classe "
            "sugerida, não diverge o bastante da classe atual ou não está ativa na fila.")


def override_removido(s: Solicitacao) -> str | None:
    """Texto para o log, se aprovar vai remover um override do regulador (`classe_medico`, D-100)."""
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


def classe_decidida(solicitacao: Solicitacao, acao: AcaoDecisao, classe_sugerida: Classe,
                    classe: Classe | None) -> Classe:
    s = solicitacao
    if acao == AcaoDecisao.APROVAR:
        return classe_sugerida
    if acao == AcaoDecisao.MANTER:
        return s.classe_medico or classe_referencia(s.classe_status, s.classe_confirmada,
                                                    s.prioridade_norm, s.classe_vigente)
    return classe or s.classe_medico or classe_sugerida


def aplicar_decisao(solicitacao: Solicitacao, acao: AcaoDecisao, classe_sugerida: Classe,
                    classe: Classe | None, score: float | None,
                    motivo: MotivoCodificado | None, regulador_id: str,
                    editado_em: datetime) -> Classe:
    """Atualiza o estado da solicitação e devolve a classe decidida.

    `editado_em` é a data de referência da edição (derivada de REF, não do relógio): é dela
    que o score editado envelhece. O horário real fica no log de decisões.
    """
    s = solicitacao
    decidida = classe_decidida(s, acao, classe_sugerida, classe)
    # Vale para a classe final (inclusive manter/editar só score), antes de mexer no estado.
    if decidida in CLASSES_PROIBIDAS_ONCOLOGICO and is_oncologico(s.cid_principal):
        raise OncologicoRebaixadoError()
    if acao == AcaoDecisao.APROVAR:  # D-100: o override sai inteiro (o log guarda o que era)
        s.classe_medico, s.score_medico = None, None
        s.editado_manualmente = False
        s.editado_por, s.editado_em = None, None
    else:
        if acao == AcaoDecisao.EDITAR:
            if score is not None:
                s.score_medico = score
            elif decidida != s.classe_medico:
                s.score_medico = None  # score antigo era de outra classe
        s.classe_medico = decidida
        s.editado_manualmente = True
        s.editado_por, s.editado_em = regulador_id, editado_em
        s.motivo_codificado = motivo
    s.classe_status = ClasseStatus.CONFIRMADA
    s.classe_confirmada = decidida
    s.classe_vigente = None  # decisão humana substitui a classe congelada
    return decidida
