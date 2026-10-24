"""Casos de aceite da US-08. Remova o skip ao implementar domain/ranking.py."""
from datetime import date

import pytest

from app.domain.enums import Camada
from app.domain.models import ItemRanking
from app.domain.ranking import ordenar_fila

pytestmark = pytest.mark.skip(reason="US-08 ainda não implementada")


def _item(sid, onco=False, urg=False, score=0.0, entrada=date(2025, 1, 1)):
    return ItemRanking(sid, onco, urg, score, entrada)


def test_oncologico_acima_de_nao_urgente_mesmo_com_score_menor():
    fila = ordenar_fila([_item("NAO-URG", score=111.0), _item("ONCO", onco=True, score=25.0)])
    assert [i.solicitacao_id for i in fila] == ["ONCO", "NAO-URG"]
    assert fila[0].camada == Camada.ONCOLOGICO


def test_camadas_em_ordem_e_posicoes_sem_buraco():
    fila = ordenar_fila([_item("C3", score=999), _item("C2", urg=True, score=1),
                         _item("C1", onco=True, score=1)])
    assert [i.camada for i in fila] == [Camada.ONCOLOGICO, Camada.URGENTE, Camada.DEMAIS]
    assert [i.posicao for i in fila] == [1, 2, 3]


def test_desempate_pela_entrada_mais_antiga():
    fila = ordenar_fila([_item("NOVO", score=50, entrada=date(2026, 1, 1)),
                         _item("ANTIGO", score=50, entrada=date(2023, 1, 1))])
    assert fila[0].solicitacao_id == "ANTIGO"
