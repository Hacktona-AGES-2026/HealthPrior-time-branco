"""US-21 · GET /solicitacoes/{id}: detalhe e explicação de um paciente (só leitura).

O score é recalculado na leitura com o SWALIS (C-07); posição e camada vêm da fila publicada (US-10).
Nenhuma regra de ranking aqui.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe, ClasseStatus, StatusFila
from app.domain.errors import NaoEncontradoError
from app.domain.explicacao import camada_motivo, montar_explicacao
from app.domain.models import Correcao, Decisao, Evento, Motivo, Pendencia, ResultadoScore, Solicitacao
from app.domain.ports import (
    DecisaoRepository,
    CorrecaoRepository,
    EventoRepository,
    FilaRepository,
    PendenciaRepository,
    SolicitacaoRepository,
    SwalisScorer,
)


@dataclass
class ScoreDetalhe:
    classe_sistema: Classe | None
    score_sistema: float | None
    classe_medico: Classe | None
    score_medico: float | None
    score_efetivo: float | None
    prazo_dias: int | None
    pct_prazo_consumido: float | None
    classe_status: ClasseStatus
    versao_regras: str | None
    motivos: list[Motivo] = field(default_factory=list)


@dataclass
class EventoVisao:
    evento_id: str
    data_evento: date
    tipo_evento: str
    resultado: str | None
    descricao: str
    historico: bool
    duplicado: bool  # duplicado_de não nulo (PRE-07)


@dataclass
class DetalheSolicitacao:
    solicitacao: Solicitacao
    score: ScoreDetalhe
    posicao: int | None
    camada: int | None
    camada_motivo: str | None
    explicacao: str
    eventos: list[EventoVisao]
    correcoes: list[Correcao]
    pendencias: list[Pendencia]
    decisoes: list[Decisao] = field(default_factory=list)  # log do regulador (US-13/14)


class DetalharSolicitacao:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 correcoes: CorrecaoRepository, pendencias: PendenciaRepository,
                 fila: FilaRepository, scorer: SwalisScorer, ref_date: date,
                 decisoes: DecisaoRepository | None = None):
        self._decisoes = decisoes
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._correcoes = correcoes
        self._pendencias = pendencias
        self._fila = fila
        self._scorer = scorer
        self._ref_date = ref_date

    def executar(self, solicitacao_id: str) -> DetalheSolicitacao:
        sol = self._solicitacoes.obter(solicitacao_id)
        if sol is None:
            raise NaoEncontradoError(f"Solicitação {solicitacao_id} não encontrada.")

        eventos = self._eventos.listar_por_solicitacao(solicitacao_id)
        res = self._scorer.calcular(sol, eventos)
        score = _score(sol, res, self._ref_date)
        linha = next((l for l in self._fila.obter_publicada()
                      if l.solicitacao_id == solicitacao_id), None)
        classe_efetiva = sol.classe_medico if sol.classe_medico is not None else res.classe_sistema
        dias_em_fila = (self._ref_date - sol.data_entrada_fila).days

        return DetalheSolicitacao(
            solicitacao=sol,
            score=score,
            posicao=linha.posicao if linha else None,
            camada=linha.camada if linha else None,
            camada_motivo=camada_motivo(linha.camada if linha else None, sol.cid_principal,
                                        linha.justificativa if linha else None),
            explicacao=montar_explicacao(
                posicao=linha.posicao if linha else None,
                camada=linha.camada if linha else None,
                cid=sol.cid_principal,
                classe=classe_efetiva.value,
                prazo_dias=score.prazo_dias,
                pct_prazo=score.pct_prazo_consumido,
                dias_em_fila=dias_em_fila,
                motivos=[m.evidencia for m in res.motivos],
                editado_manualmente=sol.editado_manualmente,
                editado_por=sol.editado_por,
                status_fila=sol.status_fila.value,
                motivo_status=sol.motivo_status,
            ),
            eventos=[_evento_visao(e) for e in sorted(eventos,
                                                      key=lambda e: (e.data_evento, e.evento_id))],
            correcoes=self._correcoes.listar_por_solicitacao(solicitacao_id),
            pendencias=self._pendencias.listar_por_solicitacao(solicitacao_id),
            decisoes=(self._decisoes.listar_por_solicitacao(solicitacao_id)
                      if self._decisoes else []),
        )


def _score(sol: Solicitacao, res: ResultadoScore, ref_date: date) -> ScoreDetalhe:
    prazo, pct = res.prazo_dias, res.pct_prazo_consumido
    if sol.classe_medico is not None:
        # Classe editada pelo regulador: prazo e % acompanham a classe decidida (como em montar_fila).
        prazo = PRAZO_MAXIMO_DIAS[sol.classe_medico]
        pct = round(100 * (ref_date - sol.data_entrada_fila).days / prazo, 1)
    score_efetivo = sol.score_medico if sol.score_medico is not None else res.score_sistema
    if sol.score_medico is None and sol.classe_medico is not None:
        score_efetivo = round(pct * res.fator_contexto, 1)  # fatores valem com a classe do regulador
    return ScoreDetalhe(
        classe_sistema=res.classe_sistema, score_sistema=res.score_sistema,
        classe_medico=sol.classe_medico, score_medico=sol.score_medico,
        score_efetivo=score_efetivo, prazo_dias=prazo, pct_prazo_consumido=pct,
        classe_status=sol.classe_status, versao_regras=res.versao_regras, motivos=res.motivos,
    )


def _evento_visao(e: Evento) -> EventoVisao:
    return EventoVisao(evento_id=e.evento_id, data_evento=e.data_evento, tipo_evento=e.tipo_evento,
                       resultado=e.resultado, descricao=e.descricao, historico=e.historico,
                       duplicado=e.duplicado_de is not None)
