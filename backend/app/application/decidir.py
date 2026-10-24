"""US-13/14 · Decisão do regulador (C-09, C-10).

- aprovar: confirma a classe sugerida.
- editar: override de classe ou score, com motivo + justificativa obrigatórios.
- manter: recusa a sugestão, com motivo + justificativa.
Bloqueia edição que rebaixe oncológico (I-01) -> OncologicoRebaixadoError.
Aprovar só vale para o que o inbox mostraria (409 SEM_PROPOSTA, D-94) e o log diz que override
saiu (D-95). Edita classe/score, nunca posição (D-03).

A decisão é gravada e **confirmada** antes; só então a fila é refeita pelo portão do verificador
(C-11, C-12), em transação própria: a publicação desfaz a *própria* transação quando reprova. Se ela
reprovar ou falhar, a decisão continua valendo, a fila anterior segue publicada (I-07) e
`fila_publicada = false` (D-73, D-96).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Protocol

from app.domain.decisao import aplicar_decisao, override_removido, validar_decisao, validar_proposta
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


class Publicador(Protocol):
    def executar(self): ...


def _posicao(fila: FilaRepository, solicitacao_id: str) -> int | None:
    return next((l.posicao for l in fila.obter_publicada() if l.solicitacao_id == solicitacao_id), None)


class DecidirClasse:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 decisoes: DecisaoRepository, scorer: SwalisScorer, uow: UnidadeDeTrabalho,
                 publicar: Publicador, fila: FilaRepository, relogio: Callable[[], datetime],
                 ref_date: date):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._decisoes = decisoes
        self._scorer = scorer
        self._uow = uow
        self._publicar = publicar
        self._fila = fila
        self._relogio = relogio
        self._ref_date = ref_date

    def executar(self, c: ComandoDecisao) -> ResultadoDecisao:
        anterior = _posicao(self._fila, c.solicitacao_id)
        try:
            decisao_id = self._decidir(c)
            self._uow.confirmar()  # a decisão vale mesmo se a nova fila não passar no verificador
        except Exception:
            self._uow.desfazer()
            raise
        publicada = self._republicar()
        # sem republicar, a fila publicada é a anterior: a posição não mudou
        nova = _posicao(self._fila, c.solicitacao_id) if publicada else anterior
        return ResultadoDecisao(decisao_id, anterior, nova, publicada)

    def _decidir(self, c: ComandoDecisao) -> str:
        s = self._solicitacoes.obter(c.solicitacao_id)
        if s is None:
            raise NaoEncontradoError(f"Solicitação {c.solicitacao_id} não encontrada.")
        validar_decisao(s, c.acao, c.classe, c.score, c.motivo_codificado, c.justificativa)
        res = self._scorer.calcular(s, self._eventos.listar_por_solicitacao(s.solicitacao_id))
        removido = None
        if c.acao == AcaoDecisao.APROVAR:
            validar_proposta(s, res.classe_sistema)
            removido = override_removido(s)
        agora = self._relogio()  # auditoria (log de decisões)
        # A fila envelhece a partir de REF, nunca do relógio da máquina.
        editado_em = datetime(self._ref_date.year, self._ref_date.month, self._ref_date.day,
                              tzinfo=timezone.utc)
        decidida = aplicar_decisao(s, c.acao, res.classe_sistema, c.classe, c.score,
                                   c.motivo_codificado, c.regulador_id, editado_em)
        justificativa = "\n".join(t for t in ((c.justificativa or "").strip(), removido) if t) or None
        decisao = Decisao(
            decisao_id=self._decisoes.proximo_id(), solicitacao_id=s.solicitacao_id,
            regulador_id=c.regulador_id, acao=c.acao, data=agora,
            classe_sugerida=res.classe_sistema, classe_decidida=decidida,
            score_decidido=c.score, motivo_codificado=c.motivo_codificado,
            justificativa=justificativa, versao_regras=res.versao_regras,
            procedimento_id=s.procedimento_id)
        self._solicitacoes.salvar(s)
        self._decisoes.adicionar(decisao)
        return decisao.decisao_id

    def _republicar(self) -> bool:
        try:
            return self._publicar.executar().publicada
        except Exception:  # a decisão já foi confirmada: não esconder isso atrás de um 500 (D-96)
            log.exception("Decisão confirmada, mas a fila não foi republicada")
            return False
