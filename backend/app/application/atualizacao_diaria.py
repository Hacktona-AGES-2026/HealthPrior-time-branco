"""US-16 · Atualização diária (C-13, passos 1, 2 e 4): avança a data de referência e republica.

A fila é recalculada do zero a partir da data (não soma +1 no que está gravado), então rodar de
novo com a mesma data dá a mesma fila. Os eventos "só registrados" já estão no banco e entram no
recálculo; trava + verificador ficam no `PublicarFila` (I-07). Recontato (passo 3) é a US-17.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from app.application.publicar_fila import PublicarFila, ResultadoPublicacao
from app.domain.errors import DataReferenciaInvalidaError
from app.domain.ports import FilaRepository


class AtualizacaoDiaria:
    def __init__(
        self,
        fila: FilaRepository,
        publicar_em: Callable[[date], PublicarFila],
        data_oficial: date,
    ):
        # `publicar_em(data)` monta GerarFila e SWALIS com a mesma data (uma data por execução).
        self._fila = fila
        self._publicar_em = publicar_em
        self._data_oficial = data_oficial

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
        return self._publicar_em(self.proxima_data(data)).executar()
