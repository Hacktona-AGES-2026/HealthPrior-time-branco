"""C-05 · Pré-processamento (PRE-xx) sobre o que já está no banco.

Hoje aplica PRE-05..08 (US-03): oncológico pelo CID, piora pelos eventos, e marca eventos
duplicados e históricos. Idempotente: recalcula tudo e refaz o log dessas regras; as colunas
originais nunca mudam. A normalização PRE-01..04 (US-02) entra neste mesmo fluxo.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.domain.models import Correcao, Evento
from app.domain.ports import (
    CorrecaoRepository,
    EventoRepository,
    SolicitacaoRepository,
    UnidadeDeTrabalho,
)
from app.domain.preprocessing.flags import REGRAS_FLAGS, marcar_eventos, recalcular_flags


@dataclass
class ResumoPreprocessamento:
    solicitacoes: int = 0
    eventos_duplicados: int = 0
    eventos_historicos: int = 0
    correcoes: dict[str, int] = field(default_factory=dict)  # por regra (PRE-xx)


class Preprocessar:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 correcoes: CorrecaoRepository, unidade: UnidadeDeTrabalho):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._correcoes = correcoes
        self._unidade = unidade

    def executar(self) -> ResumoPreprocessamento:
        try:
            resumo = self._processar()
            self._unidade.confirmar()
        except Exception:
            self._unidade.desfazer()
            raise
        return resumo

    def _processar(self) -> ResumoPreprocessamento:
        solicitacoes = self._solicitacoes.listar(apenas_ativas=False)
        por_solicitacao: dict[str, list[Evento]] = defaultdict(list)
        for e in self._eventos.listar_todos():
            por_solicitacao[e.solicitacao_id].append(e)

        correcoes: list[Correcao] = []
        marcados: list[Evento] = []
        for s in solicitacoes:
            eventos = marcar_eventos(s, por_solicitacao.get(s.solicitacao_id, []))
            correcoes.extend(recalcular_flags(s, eventos))
            marcados.extend(eventos)

        self._solicitacoes.atualizar_flags(solicitacoes)
        self._eventos.atualizar_marcas(marcados)
        self._correcoes.substituir_por_regras(REGRAS_FLAGS, correcoes)

        return ResumoPreprocessamento(
            solicitacoes=len(solicitacoes),
            eventos_duplicados=sum(1 for e in marcados if e.duplicado_de),
            eventos_historicos=sum(1 for e in marcados if e.historico),
            correcoes=dict(Counter(c.regra for c in correcoes)),
        )
