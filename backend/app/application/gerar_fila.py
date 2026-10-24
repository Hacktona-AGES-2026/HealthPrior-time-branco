"""US-09 · Gera a fila priorizada a partir do banco e exporta o fila_priorizada.csv (C-11).

Fluxo: solicitações ativas + eventos -> score (SWALIS) -> trava por camadas -> CSV.
Verificar o CSV e publicar a fila (I-07) ficam na US-10 (`PublicarFila`).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.application.montar_fila import linhas_para_dicts, montar_fila
from app.domain.models import Evento, LinhaFila
from app.domain.ports import EventoRepository, SolicitacaoRepository, SwalisScorer


@dataclass
class ResultadoGeracao:
    """Resumo da geração: as linhas, onde o CSV foi escrito e contagens."""

    linhas: list[LinhaFila]
    caminho_csv: Path
    total: int
    versao_regras: str
    por_camada: dict[int, int]
    ref_date: date


class GerarFila:
    def __init__(
        self,
        solicitacoes: SolicitacaoRepository,
        eventos: EventoRepository,
        scorer: SwalisScorer,
        exportador,
        ref_date: date,
    ):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._scorer = scorer
        self._exportador = exportador
        self._ref_date = ref_date

    def executar(self, caminho_csv: Path) -> ResultadoGeracao:
        """Monta a fila das solicitações ativas e exporta o CSV em `caminho_csv`."""
        ativas = self._solicitacoes.listar(apenas_ativas=True)
        ids = {s.solicitacao_id for s in ativas}
        por_solicitacao: dict[str, list[Evento]] = {}
        for ev in self._eventos.listar_todos():
            if ev.solicitacao_id in ids:
                por_solicitacao.setdefault(ev.solicitacao_id, []).append(ev)
        linhas = montar_fila(ativas, por_solicitacao, self._scorer, self._ref_date)
        self._exportador.exportar(linhas_para_dicts(linhas), caminho_csv)
        contagem = Counter(l.camada for l in linhas)
        return ResultadoGeracao(
            linhas=linhas,
            caminho_csv=caminho_csv,
            total=len(linhas),
            versao_regras=self._scorer.versao_regras,
            por_camada=dict(sorted(contagem.items())),
            ref_date=self._ref_date,
        )
