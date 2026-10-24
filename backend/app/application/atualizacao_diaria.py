"""US-16 · Atualização diária (C-13, passos 1, 2 e 4): avança a data de referência e republica.

A fila é recalculada do zero a partir da data (não soma +1 no que está gravado), então rodar de
novo com a mesma data dá a mesma fila. Os eventos "só registrados" já estão no banco e entram no
recálculo; trava + verificador ficam no `PublicarFila` (I-07). O recontato (passo 3, US-17) roda antes
de publicar e é confirmado antes: a publicação desfaz a própria transação se o verificador reprovar.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from app.application.detectar_recontato import DetectarRecontato, ResumoRecontato
from app.application.publicar_fila import PublicarFila, ResultadoPublicacao
from app.domain.errors import DataReferenciaInvalidaError
from app.domain.ports import FilaRepository, UnidadeDeTrabalho


class AtualizacaoDiaria:
    def __init__(
        self,
        fila: FilaRepository,
        publicar_em: Callable[[date], PublicarFila],
        data_oficial: date,
        recontato_em: Callable[[date], DetectarRecontato] | None = None,
        uow: UnidadeDeTrabalho | None = None,
    ):
        # `publicar_em(data)` monta GerarFila e SWALIS com a mesma data (uma data por execução).
        self._fila = fila
        self._publicar_em = publicar_em
        self._data_oficial = data_oficial
        self._recontato_em = recontato_em  # US-17: passo 3 do C-13
        self._uow = uow

    def proxima_data(self, data: date | None = None) -> date:
        """`data` se informada; senão a da última fila publicada (ou a oficial) + 1 dia."""
        if data is None:
            data = (self._fila.data_referencia() or self._data_oficial) + timedelta(days=1)
        if data < self._data_oficial:
            raise DataReferenciaInvalidaError(
                f"A data de referência não pode ser anterior a {self._data_oficial.isoformat()} "
                "(data oficial do dataset).")
        return data

    def executar(self, data: date | None = None) -> ResultadoPublicacao:
        data = self.proxima_data(data)
        recontato: ResumoRecontato | None = None
        if self._recontato_em is not None:
            recontato = self._recontato_em(data).executar()
            if self._uow is not None:
                self._uow.confirmar()
        resultado = self._publicar_em(data).executar()
        resultado.recontato = recontato
        return resultado
