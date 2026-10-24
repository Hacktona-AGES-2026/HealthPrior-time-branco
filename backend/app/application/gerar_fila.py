"""US-08/09/10 · Gera, verifica e publica a fila priorizada (C-11, C-12).

Fluxo: solicitações ativas -> score (SWALIS) -> trava por camadas -> CSV -> verificador -> publica.
Se o verificador falhar, NÃO publica e mantém a fila anterior (I-07).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.ports import (
    EventoRepository,
    FilaRepository,
    SolicitacaoRepository,
    SwalisScorer,
    VerificadorFila,
)


@dataclass
class ResultadoGeracao:
    publicada: bool
    caminho_csv: Path
    total: int
    saida_verificador: str


class GerarFila:
    def __init__(
        self,
        solicitacoes: SolicitacaoRepository,
        eventos: EventoRepository,
        scorer: SwalisScorer,
        verificador: VerificadorFila,
        fila: FilaRepository,
        exportador,
        output_dir: Path,
    ):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._scorer = scorer
        self._verificador = verificador
        self._fila = fila
        self._exportador = exportador
        self._output_dir = output_dir

    def executar(self) -> ResultadoGeracao:
        """TODO(US-08/09/10):
        1. listar ativas; para cada uma, scorer.calcular(...) e montar ItemRanking
           (score_efetivo = score_medico ou score_sistema).
        2. domain.ranking.ordenar_fila(itens).
        3. exportador.exportar(...) para output_dir/fila_priorizada.csv com justificativa.
        4. verificador.verificar(csv); se passou -> fila.salvar_publicada(...).
        """
        raise NotImplementedError("US-08/09/10: GerarFila.executar")
