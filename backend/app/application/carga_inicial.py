"""US-01 · Carga inicial (C-02).

Lê o dataset e grava com os valores originais, sem alterar nada. Em seguida, se houver um
`Preprocessar`, recalcula as colunas derivadas (PRE-xx) em colunas novas, numa segunda transação:
se ela falhar, a carga fica gravada e basta rodar o pré-processamento de novo.
Não passa pelo regulador (D-01). Idempotente: repetir não duplica.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.preprocessar import Preprocessar, ResumoPreprocessamento
from app.domain.models import ResultadoTabela
from app.domain.ports import CargaRepository


@dataclass
class ResumoCarga:
    procedimentos: ResultadoTabela
    solicitacoes: ResultadoTabela
    eventos: ResultadoTabela
    preprocessamento: ResumoPreprocessamento | None = None


class CargaInicial:
    def __init__(self, leitor, repositorio: CargaRepository,
                 preprocessar: Preprocessar | None = None):
        # `leitor` é infrastructure.csv_loader.LeitorDataset (injetado para facilitar teste).
        self._leitor = leitor
        self._repositorio = repositorio
        self._preprocessar = preprocessar

    def executar(self) -> ResumoCarga:
        # Lê tudo antes de gravar: um arquivo inválido não deixa carga pela metade.
        resultado = self._repositorio.gravar(
            procedimentos=self._leitor.procedimentos(),
            solicitacoes=self._leitor.fila(),
            eventos=self._leitor.eventos(),
        )
        preprocessamento = self._preprocessar.executar() if self._preprocessar else None
        return ResumoCarga(**resultado, preprocessamento=preprocessamento)
