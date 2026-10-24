"""US-13/14 · Regras da decisão do regulador (C-09, C-10). Funções puras.

- aprovar: confirma a classe sugerida pelo SWALIS (desfaz override anterior, de forma explícita).
- editar: override de classe e/ou score; motivo + justificativa obrigatórios.
- manter: recusa a sugestão e fixa a classe atual; motivo + justificativa obrigatórios.
Edita classe/score, nunca posição (D-03).
"""
from __future__ import annotations

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
        if score is not None and score < 0:
            raise DecisaoInvalidaError("score não pode ser negativo.")
        if classe in CLASSES_PROIBIDAS_ONCOLOGICO and is_oncologico(solicitacao.cid_principal):
            raise OncologicoRebaixadoError()


def aplicar_decisao(solicitacao: Solicitacao, acao: AcaoDecisao, classe_sugerida: Classe,
                    classe: Classe | None, score: float | None,
                    motivo: MotivoCodificado | None, regulador_id: str,
                    agora: datetime) -> Classe:
    """Atualiza o estado da solicitação e devolve a classe decidida."""
    s = solicitacao
    if acao == AcaoDecisao.APROVAR:
        decidida = classe_sugerida
        s.classe_medico, s.score_medico = None, None
        s.editado_manualmente = False
    else:
        if acao == AcaoDecisao.MANTER:
            decidida = s.classe_medico or classe_referencia(s.classe_status, s.classe_confirmada,
                                                             s.prioridade_norm)
            s.classe_medico = decidida
        else:  # editar
            decidida = classe or s.classe_medico or classe_sugerida
            s.classe_medico = decidida
            if score is not None:
                s.score_medico = score
        s.editado_manualmente = True
        s.editado_por, s.editado_em = regulador_id, agora
        s.motivo_codificado = motivo
    s.classe_status = ClasseStatus.CONFIRMADA
    s.classe_confirmada = decidida
    return decidida
