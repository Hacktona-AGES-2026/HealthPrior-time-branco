"""US-12 · GET /inbox: calculado na leitura (sem tabela de propostas).

Para cada solicitação ativa presente na fila publicada, roda o SWALIS e aplica a regra do inbox.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import Classe
from app.domain.inbox import chave_ordenacao, classe_referencia, distancia, entra_no_inbox
from app.domain.models import Motivo
from app.domain.ports import (
    DecisaoRepository,
    EventoRepository,
    FilaRepository,
    SolicitacaoRepository,
    SwalisScorer,
)


@dataclass
class ItemInbox:
    solicitacao_id: str
    procedimento: str
    camada: int
    dias_em_fila: int
    classe_atual: Classe
    classe_sugerida: Classe
    motivos: list[Motivo] = field(default_factory=list)
    evento_gatilho: str | None = None
    editado_anteriormente: tuple[str, datetime] | None = None
    criado_em: datetime | None = None


@dataclass
class Inbox:
    total: int
    itens: list[ItemInbox]


class ListarInbox:
    def __init__(self, fila: FilaRepository, solicitacoes: SolicitacaoRepository,
                 eventos: EventoRepository, scorer: SwalisScorer,
                 decisoes: DecisaoRepository | None = None):
        self._decisoes = decisoes
        self._fila = fila
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._scorer = scorer

    def executar(self) -> Inbox:
        linhas = self._fila.obter_publicada()
        if not linhas:
            return Inbox(0, [])
        publicada_em = self._fila.publicada_em()
        por_id = {s.solicitacao_id: s for s in self._solicitacoes.listar(apenas_ativas=True)}
        eventos_por_id: dict[str, list] = defaultdict(list)
        for e in self._eventos.listar_todos():
            eventos_por_id[e.solicitacao_id].append(e)

        candidatos = []
        for linha in linhas:
            s = por_id.get(linha.solicitacao_id)
            if s is None:
                continue
            res = self._scorer.calcular(s, eventos_por_id.get(s.solicitacao_id, []))
            sugerida = res.classe_sistema
            if not entra_no_inbox(sugerida, s.classe_status, s.classe_confirmada,
                                  s.prioridade_norm, s.classe_vigente):
                continue
            if self._ja_avaliada(s.solicitacao_id, sugerida):
                continue
            atual = classe_referencia(s.classe_status, s.classe_confirmada, s.prioridade_norm,
                                      s.classe_vigente)
            dist = distancia(sugerida, atual)
            gatilho = next((m.ref for m in res.motivos if m.fonte == "evento" and m.ref), None)
            editado = ((s.editado_por, s.editado_em)
                       if s.editado_por and s.editado_em else None)
            item = ItemInbox(
                solicitacao_id=s.solicitacao_id, procedimento=s.procedimento or "",
                camada=linha.camada, dias_em_fila=linha.dias_em_fila,
                classe_atual=atual, classe_sugerida=sugerida, motivos=list(res.motivos),
                evento_gatilho=gatilho, editado_anteriormente=editado, criado_em=publicada_em)
            candidatos.append((chave_ordenacao(sugerida, dist, linha.posicao), item))

        candidatos.sort(key=lambda par: par[0])
        itens = [i for _, i in candidatos]
        return Inbox(len(itens), itens)

    def _ja_avaliada(self, solicitacao_id: str, sugerida: Classe) -> bool:
        """O regulador já decidiu sobre esta mesma sugestão (editou ou manteve): não volta ao inbox
        até a sugestão mudar (D-77)."""
        if self._decisoes is None:
            return False
        decisoes = self._decisoes.listar_por_solicitacao(solicitacao_id)
        return bool(decisoes) and decisoes[-1].classe_sugerida == sugerida
