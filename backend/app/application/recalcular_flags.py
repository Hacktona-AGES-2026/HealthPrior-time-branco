"""US-03 · Flags recalculadas e eventos limpos (C-05, PRE-05..PRE-08).

Oncológico pelo CID, piora pelos eventos, e marca de eventos duplicados e históricos (nenhum
evento é apagado). Idempotente: recalcula tudo e refaz só o log das suas regras, sem tocar nas
colunas originais. Não confirma a transação (ver UnidadeDeTrabalho): a carga confirma tudo junto.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.domain.models import Correcao, Evento
from app.domain.ports import CorrecaoRepository, EventoRepository, SolicitacaoRepository
from app.domain.preprocessing.flags import REGRAS_FLAGS, marcar_eventos, recalcular_flags


@dataclass
class ResumoFlags:
    solicitacoes: int = 0
    eventos_duplicados: int = 0
    eventos_historicos: int = 0
    correcoes: dict[str, int] = field(default_factory=dict)  # por regra (PRE-xx)


class RecalcularFlags:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 correcoes: CorrecaoRepository):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._correcoes = correcoes

    def executar(self) -> ResumoFlags:
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
        self._correcoes.substituir(REGRAS_FLAGS, correcoes)

        return ResumoFlags(
            solicitacoes=len(solicitacoes),
            eventos_duplicados=sum(1 for e in marcados if e.duplicado_de),
            eventos_historicos=sum(1 for e in marcados if e.historico),
            correcoes=dict(Counter(c.regra for c in correcoes)),
        )
