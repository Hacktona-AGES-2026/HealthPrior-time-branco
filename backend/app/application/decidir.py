"""US-13/14 · Decisão do regulador (C-09, C-10).

- aprovar: confirma a classe sugerida.
- editar: override de classe ou score, com motivo + justificativa obrigatórios.
- manter: recusa a sugestão, com motivo + justificativa.
Bloqueia edição que rebaixe oncológico (I-01) -> OncologicoRebaixadoError.
Edita classe/score, nunca posição (D-03). Depois de gravar, refaz a fila pelo portão do
verificador (C-11, C-12): se o verificador reprovar, a decisão fica e a fila anterior continua.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from app.domain.decisao import aplicar_decisao, validar_decisao
from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado
from app.domain.errors import NaoEncontradoError
from app.domain.models import Decisao
from app.domain.ports import (
    DecisaoRepository,
    EventoRepository,
    FilaRepository,
    SolicitacaoRepository,
    SwalisScorer,
    UnidadeDeTrabalho,
)


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


class Publicador(Protocol):
    def executar(self): ...


def _posicao(fila: FilaRepository, solicitacao_id: str) -> int | None:
    return next((l.posicao for l in fila.obter_publicada() if l.solicitacao_id == solicitacao_id), None)


class DecidirClasse:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 decisoes: DecisaoRepository, scorer: SwalisScorer, uow: UnidadeDeTrabalho,
                 publicar: Publicador, fila: FilaRepository, relogio: Callable[[], datetime],
                 gerar_id: Callable[[], str] = lambda: f"DEC-{uuid.uuid4().hex[:10]}"):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._decisoes = decisoes
        self._scorer = scorer
        self._uow = uow
        self._publicar = publicar
        self._fila = fila
        self._relogio = relogio
        self._gerar_id = gerar_id

    def executar(self, c: ComandoDecisao) -> ResultadoDecisao:
        s = self._solicitacoes.obter(c.solicitacao_id)
        if s is None:
            raise NaoEncontradoError(f"Solicitação {c.solicitacao_id} não encontrada.")
        validar_decisao(s, c.acao, c.classe, c.score, c.motivo_codificado, c.justificativa)
        res = self._scorer.calcular(s, self._eventos.listar_por_solicitacao(s.solicitacao_id))
        agora = self._relogio()
        decidida = aplicar_decisao(s, c.acao, res.classe_sistema, c.classe, c.score,
                                   c.motivo_codificado, c.regulador_id, agora)
        decisao = Decisao(
            decisao_id=self._gerar_id(), solicitacao_id=s.solicitacao_id,
            regulador_id=c.regulador_id, acao=c.acao, data=agora,
            classe_sugerida=res.classe_sistema, classe_decidida=decidida,
            score_decidido=c.score, motivo_codificado=c.motivo_codificado,
            justificativa=(c.justificativa or "").strip() or None,
            versao_regras=res.versao_regras)
        anterior = _posicao(self._fila, s.solicitacao_id)
        self._solicitacoes.salvar(s)
        self._decisoes.adicionar(decisao)
        self._uow.confirmar()  # a decisão vale mesmo se a nova fila não passar no verificador
        publicada = self._publicar.executar().publicada
        nova = _posicao(self._fila, s.solicitacao_id) if publicada else anterior
        return ResultadoDecisao(decisao.decisao_id, anterior, nova, publicada)
