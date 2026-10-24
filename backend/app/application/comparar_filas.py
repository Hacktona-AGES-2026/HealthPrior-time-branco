"""US-22 · Compara a fila 'antes' (ordem atual do hospital) com a 'depois' (fila publicada)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.metricas import (
    IndicadoresFila,
    calcular_indicadores,
    com_ps_recente,
    is_sem_urgencia_verificador,
    ordem_atual,
)
from app.domain.models import Evento
from app.domain.ports import EventoRepository, FilaRepository, SolicitacaoRepository


@dataclass
class Destaque:
    solicitacao_id: str
    posicao_antes: int | None
    posicao_depois: int | None
    camada_depois: int | None


@dataclass
class Comparacao:
    antes: IndicadoresFila
    depois: IndicadoresFila | None
    publicada: bool
    destaques: list[Destaque] = field(default_factory=list)


class CompararFilas:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 fila: FilaRepository, ref_date: date, destaques: list[str]):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._fila = fila
        self._ref_date = ref_date
        self._destaques = destaques

    def executar(self) -> Comparacao:
        todas = self._solicitacoes.listar(apenas_ativas=False)
        por_sol: dict[str, list[Evento]] = {}
        for e in self._eventos.listar_todos():
            por_sol.setdefault(e.solicitacao_id, []).append(e)

        oncologicos = {s.solicitacao_id for s in todas if s.oncologico}
        sem_urgencia = {s.solicitacao_id for s in todas
                        if is_sem_urgencia_verificador(s, por_sol.get(s.solicitacao_id, []))}
        ps_recente = com_ps_recente(por_sol, self._ref_date)

        ordem_antes = ordem_atual(todas)
        antes = calcular_indicadores(ordem_antes, oncologicos, sem_urgencia, ps_recente)
        pos_antes = {sid: i for i, sid in enumerate(ordem_antes, start=1)}

        linhas = sorted(self._fila.obter_publicada(), key=lambda l: l.posicao)
        if not linhas:
            destaques = [Destaque(sid, pos_antes.get(sid), None, None) for sid in self._destaques]
            return Comparacao(antes=antes, depois=None, publicada=False, destaques=destaques)

        ordem_depois = [l.solicitacao_id for l in linhas]
        depois = calcular_indicadores(ordem_depois, oncologicos, sem_urgencia, ps_recente)
        por_id = {l.solicitacao_id: l for l in linhas}
        destaques = [
            Destaque(sid, pos_antes.get(sid),
                     por_id[sid].posicao if sid in por_id else None,
                     por_id[sid].camada if sid in por_id else None)
            for sid in self._destaques
        ]
        return Comparacao(antes=antes, depois=depois, publicada=True, destaques=destaques)
