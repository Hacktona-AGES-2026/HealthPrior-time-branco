"""US-13/14 · Decisão do regulador (C-09, C-10).

- aprovar: confirma a classe sugerida.
- editar: override de classe ou score, com motivo + justificativa obrigatórios.
- manter: recusa a sugestão, com motivo + justificativa.
Bloqueia edição que rebaixe oncológico abaixo de não urgente (I-01) -> OncologicoRebaixadoError.
Edita classe/score, nunca posição (D-03).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado


@dataclass
class ComandoDecisao:
    solicitacao_id: str
    regulador_id: str
    acao: AcaoDecisao
    classe: Classe | None = None
    score: float | None = None
    motivo_codificado: MotivoCodificado | None = None
    justificativa: str | None = None


@dataclass
class ResultadoDecisao:
    decisao_id: str
    posicao_anterior: int | None
    posicao_nova: int | None
    fila_publicada: bool


class DecidirClasse:
    def __init__(self, solicitacoes, decisoes, gerar_fila):
        self._solicitacoes = solicitacoes
        self._decisoes = decisoes
        self._gerar_fila = gerar_fila

    def executar(self, comando: ComandoDecisao) -> ResultadoDecisao:
        """TODO(US-13/14)."""
        raise NotImplementedError("US-13/14: DecidirClasse.executar")
