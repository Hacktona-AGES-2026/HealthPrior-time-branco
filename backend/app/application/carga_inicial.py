"""US-01 · Carga inicial (C-02).

Lê o dataset, aplica o pré-processamento e grava. Não passa pelo regulador (D-01).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports import EventoRepository, SolicitacaoRepository


@dataclass
class ResumoCarga:
    solicitacoes: int
    eventos: int
    suspensas: int
    pendencias: int


class CargaInicial:
    def __init__(self, leitor, solicitacoes: SolicitacaoRepository, eventos: EventoRepository):
        # `leitor` é infrastructure.csv_loader.LeitorDataset (injetado para facilitar teste).
        self._leitor = leitor
        self._solicitacoes = solicitacoes
        self._eventos = eventos

    def executar(self) -> ResumoCarga:
        """TODO(US-01): ler CSVs -> entidades -> pré-processar -> salvar. Idempotente."""
        raise NotImplementedError("US-01: CargaInicial.executar")
