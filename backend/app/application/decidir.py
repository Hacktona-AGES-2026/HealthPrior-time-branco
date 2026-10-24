"""US-13/14 · Decisão do regulador (C-09, C-10).

- aprovar (US-13): confirma a classe sugerida.
- editar / manter (US-14): override de classe ou score, com motivo + justificativa obrigatórios.
  Bloqueia edição que rebaixe oncológico abaixo de não urgente (I-01) -> OncologicoRebaixadoError.
Edita classe/score, nunca posição (D-03).

Aprovar: valida que há proposta (a mesma regra do inbox), grava a confirmação e o registro no log de
decisões, **confirma a transação** e só então recalcula e publica a fila (US-09/10), em transação
própria: a publicação desfaz a *própria* transação quando o verificador reprova. Se ela falhar, a
decisão continua valendo, a fila anterior segue publicada (I-07) e `fila_publicada = false` (D-90).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.application.publicar_fila import PublicarFila
from app.domain.decisao import aprovar, validar_proposta
from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado
from app.domain.errors import NaoEncontradoError
from app.domain.ports import (
    DecisaoRepository,
    EventoRepository,
    FilaRepository,
    SolicitacaoRepository,
    SwalisScorer,
    UnidadeDeTrabalho,
)

log = logging.getLogger(__name__)


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
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 decisoes: DecisaoRepository, fila: FilaRepository, scorer: SwalisScorer,
                 uow: UnidadeDeTrabalho, publicar: PublicarFila, relogio: Callable[[], datetime]):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._decisoes = decisoes
        self._fila = fila
        self._scorer = scorer
        self._uow = uow
        self._publicar = publicar
        self._relogio = relogio

    def executar(self, comando: ComandoDecisao) -> ResultadoDecisao:
        if comando.acao != AcaoDecisao.APROVAR:
            raise NotImplementedError("US-14: editar e manter")
        posicao_anterior = self._posicao(comando.solicitacao_id)
        try:
            decisao_id = self._aprovar(comando)
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        publicada = self._republicar()
        # sem republicar, a fila publicada é a anterior: a posição não mudou
        posicao_nova = self._posicao(comando.solicitacao_id) if publicada else posicao_anterior
        return ResultadoDecisao(decisao_id, posicao_anterior, posicao_nova, publicada)

    def _aprovar(self, comando: ComandoDecisao) -> str:
        s = self._solicitacoes.obter(comando.solicitacao_id)
        if s is None:
            raise NaoEncontradoError(f"Solicitação {comando.solicitacao_id} não encontrada.")
        res = self._scorer.calcular(s, self._eventos.listar_por_solicitacao(s.solicitacao_id))
        validar_proposta(s, res.classe_sistema)
        decisao = aprovar(s, res.classe_sistema, comando.regulador_id, self._relogio(),
                          res.versao_regras, self._decisoes.proximo_id())
        self._solicitacoes.atualizar_decisao(s)
        self._decisoes.adicionar(decisao)
        return decisao.decisao_id

    def _posicao(self, solicitacao_id: str) -> int | None:
        return next((l.posicao for l in self._fila.obter_publicada() if l.solicitacao_id == solicitacao_id), None)

    def _republicar(self) -> bool:
        try:
            return self._publicar.executar().publicada
        except Exception:  # a decisão já foi confirmada: não esconder isso atrás de um 500
            log.exception("Decisão confirmada, mas a fila não foi republicada")
            return False
