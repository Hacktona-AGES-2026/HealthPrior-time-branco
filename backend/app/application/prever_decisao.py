"""GET /solicitacoes/{id}/previa: o que aprovar, editar ou manter faria, sem gravar (US-13/14)."""
from __future__ import annotations

from datetime import date

from app.application.previa import Previa, prever_decisao
from app.domain.enums import AcaoDecisao, Classe
from app.domain.errors import NaoEncontradoError
from app.domain.ports import EventoRepository, FilaRepository, SolicitacaoRepository, SwalisScorer


class PreverDecisao:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 fila: FilaRepository, scorer: SwalisScorer, ref_date: date):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._fila = fila
        self._scorer = scorer
        self._ref_date = ref_date

    def executar(self, solicitacao_id: str, acao: AcaoDecisao, classe: Classe | None = None,
                 score: float | None = None) -> Previa:
        s = self._solicitacoes.obter(solicitacao_id)
        if s is None:
            raise NaoEncontradoError(f"Solicitação {solicitacao_id} não encontrada.")
        res = self._scorer.calcular(s, self._eventos.listar_por_solicitacao(solicitacao_id))
        entradas = {x.solicitacao_id: x.data_entrada_fila
                    for x in self._solicitacoes.listar(apenas_ativas=True)}
        return prever_decisao(s, res, self._fila.obter_publicada(), entradas, self._ref_date,
                              acao, classe, score)
