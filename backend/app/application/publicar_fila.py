"""US-10 · Publica a fila só se o verificador oficial aprovar (I-07); senão a anterior continua valendo."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from app.application.gerar_fila import GerarFila
from app.application.montar_fila import linhas_para_dicts
from app.domain.errors import FilaNaoPublicadaError
from app.domain.ports import FilaRepository, UnidadeDeTrabalho, VerificadorFila

ARQUIVO_CANDIDATA = "fila_priorizada.candidata.csv"
ARQUIVO_PUBLICADO = "fila_priorizada.csv"
ARQUIVO_EXPORT = "fila_publicada.csv"


@dataclass
class ResultadoPublicacao:
    publicada: bool
    caminho_csv: Path
    total: int
    por_camada: dict[int, int]
    versao_regras: str
    saida_verificador: str
    data_referencia: date
    recontato: object | None = None  # US-17: ResumoRecontato, só na atualização diária


class PublicarFila:
    def __init__(
        self,
        gerar: GerarFila,
        verificador: VerificadorFila,
        fila: FilaRepository,
        uow: UnidadeDeTrabalho,
        relogio: Callable[[], datetime],
        output_dir: Path,
    ):
        self._gerar = gerar
        self._verificador = verificador
        self._fila = fila
        self._uow = uow
        self._relogio = relogio
        self._output_dir = output_dir

    def executar(self) -> ResultadoPublicacao:
        candidata = self._output_dir / ARQUIVO_CANDIDATA
        final = self._output_dir / ARQUIVO_PUBLICADO
        try:
            res = self._gerar.executar(candidata)
            passou, saida = self._verificador.verificar(res.caminho_csv)
            if passou:
                self._fila.salvar_publicada(res.linhas, res.versao_regras, self._relogio(),
                                            res.ref_date)
                # Promove o arquivo ANTES do commit: se a cópia falhar, o banco é desfeito e
                # arquivo e banco continuam apontando para a mesma fila anterior (D-39).
                shutil.copyfile(res.caminho_csv, final)
                self._uow.confirmar()
            else:
                self._uow.desfazer()
        except Exception:
            self._uow.desfazer()
            raise
        return ResultadoPublicacao(
            publicada=passou,
            caminho_csv=final if passou else res.caminho_csv,
            total=res.total,
            por_camada=res.por_camada,
            versao_regras=res.versao_regras,
            saida_verificador=saida,
            data_referencia=res.ref_date,
        )


class ExportarFilaPublicada:
    def __init__(self, fila: FilaRepository, exportador, output_dir: Path):
        self._fila = fila
        self._exportador = exportador
        self._output_dir = output_dir

    def executar(self) -> Path:
        linhas = self._fila.obter_publicada()
        if not linhas:
            raise FilaNaoPublicadaError()
        destino = self._output_dir / ARQUIVO_EXPORT
        self._exportador.exportar(linhas_para_dicts(linhas), destino)
        return destino
