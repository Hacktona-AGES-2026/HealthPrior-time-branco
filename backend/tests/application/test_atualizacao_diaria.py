"""US-16 · AtualizacaoDiaria com falsos (sem banco): qual data é usada em cada execução."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.application.atualizacao_diaria import AtualizacaoDiaria
from app.domain.errors import DataReferenciaInvalidaError

OFICIAL = date(2026, 10, 23)


class FilaFalsa:
    def __init__(self, data_referencia=None):
        self._data = data_referencia

    def data_referencia(self):
        return self._data


def _caso(data_publicada=None):
    datas = []

    def publicar_em(data):
        datas.append(data)
        return SimpleNamespace(executar=lambda: SimpleNamespace(publicada=True, data_referencia=data))

    return AtualizacaoDiaria(FilaFalsa(data_publicada), publicar_em, OFICIAL), datas


def test_sem_fila_publicada_parte_da_data_oficial():
    caso, datas = _caso()
    assert caso.executar().data_referencia == date(2026, 10, 24)
    assert datas == [date(2026, 10, 24)]


def test_continua_da_ultima_data_publicada():
    caso, datas = _caso(date(2026, 10, 25))
    caso.executar()
    assert datas == [date(2026, 10, 26)]


def test_data_informada_vale_e_pode_voltar_para_a_oficial():
    caso, datas = _caso(date(2026, 10, 30))
    caso.executar(date(2026, 11, 2))
    caso.executar(OFICIAL)
    assert datas == [date(2026, 11, 2), OFICIAL]


def test_data_anterior_a_oficial_e_recusada_sem_publicar():
    caso, datas = _caso()
    with pytest.raises(DataReferenciaInvalidaError):
        caso.executar(date(2026, 10, 22))
    assert datas == []
