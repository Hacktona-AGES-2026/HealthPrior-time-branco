"""US-01 · Carga inicial (C-02), seguida da normalização (US-02, D-20).

Lê o dataset e grava com os valores originais, sem alterar nada; a normalização escreve só em
colunas novas. Tudo na mesma transação: ou entra tudo, ou nada. Não passa pelo regulador (D-01).
Idempotente: repetir não duplica.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.normalizar import Normalizar, ResumoNormalizacao
from app.domain.models import ResultadoTabela
from app.domain.ports import CargaRepository, UnidadeDeTrabalho


@dataclass
class ResumoCarga:
    procedimentos: ResultadoTabela
    solicitacoes: ResultadoTabela
    eventos: ResultadoTabela
    normalizacao: ResumoNormalizacao


class CargaInicial:
    def __init__(self, leitor, repositorio: CargaRepository, normalizar: Normalizar,
                 uow: UnidadeDeTrabalho):
        # `leitor` é infrastructure.csv_loader.LeitorDataset (injetado para facilitar teste).
        self._leitor = leitor
        self._repositorio = repositorio
        self._normalizar = normalizar
        self._uow = uow

    def executar(self) -> ResumoCarga:
        # Lê tudo antes de gravar: um arquivo inválido não deixa carga pela metade.
        procedimentos = self._leitor.procedimentos()
        solicitacoes = self._leitor.fila()
        eventos = self._leitor.eventos()
        try:
            tabelas = self._repositorio.gravar(procedimentos, solicitacoes, eventos)
            normalizacao = self._normalizar.executar()
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        return ResumoCarga(**tabelas, normalizacao=normalizacao)
