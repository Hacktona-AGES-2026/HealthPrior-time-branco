"""US-01 · Carga inicial (C-02).

Lê o dataset e grava com os valores originais, sem alterar nada. A normalização (PRE-xx) entra
na US-02, em colunas novas. Não passa pelo regulador (D-01). Idempotente: repetir não duplica.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import ResultadoTabela
from app.domain.ports import CargaRepository


@dataclass
class ResumoCarga:
    procedimentos: ResultadoTabela
    solicitacoes: ResultadoTabela
    eventos: ResultadoTabela


class CargaInicial:
    def __init__(self, leitor, repositorio: CargaRepository):
        # `leitor` é infrastructure.csv_loader.LeitorDataset (injetado para facilitar teste).
        self._leitor = leitor
        self._repositorio = repositorio

    def executar(self) -> ResumoCarga:
        # Lê tudo antes de gravar: um arquivo inválido não deixa carga pela metade.
        resultado = self._repositorio.gravar(
            procedimentos=self._leitor.procedimentos(),
            solicitacoes=self._leitor.fila(),
            eventos=self._leitor.eventos(),
        )
        return ResumoCarga(**resultado)
