"""US-13/14 · Regras da decisão do regulador (C-09, C-10). Funções puras.

- aprovar: confirma a classe sugerida pelo SWALIS (desfaz override anterior, de forma explícita).
- editar: override de classe e/ou score; motivo + justificativa obrigatórios.
- manter: recusa a sugestão e fixa a classe atual; motivo + justificativa obrigatórios.
Edita classe/score, nunca posição (D-03).
"""
from __future__ import annotations

import math
from datetime import datetime

from app.domain.cid import is_oncologico
from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, MotivoCodificado
from app.domain.errors import DecisaoInvalidaError, JustificativaObrigatoriaError, OncologicoRebaixadoError
from app.domain.inbox import classe_referencia
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
    if acao == AcaoDecisao.APROVAR:
        s.classe_medico, s.score_medico = None, None
        s.editado_manualmente = False
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
