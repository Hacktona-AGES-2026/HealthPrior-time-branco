from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.domain.enums import Camada
from app.domain.models import ItemRanking
from app.domain.ranking import definir_bloco, definir_camada, ordenar_fila

DATA = date(2025, 1, 1)


def item(
    sid: str,
    *,
    oncologico: bool = False,
    urgente: bool = False,
    score: float = 0.0,
    data: date = DATA,
) -> ItemRanking:
    return ItemRanking(
        solicitacao_id=sid,
        oncologico=oncologico,
        urgente=urgente,
        score_efetivo=score,
        data_entrada_fila=data,
    )


def test_oncologico_com_score_baixo_fica_acima_de_nao_urgente_com_score_alto():
    itens = [
        item("nao_urgente", score=111),
        item("onco", oncologico=True, score=25),
    ]

    fila = ordenar_fila(itens)

    assert fila[0].solicitacao_id == "onco"
    assert fila[0].posicao == 1
    assert fila[0].camada == Camada.ONCOLOGICO
    assert fila[1].solicitacao_id == "nao_urgente"


def test_camada_3_nao_invade_o_bloco_prioritario():
    itens = [
        item("demais", score=999),
        item("urgente", urgente=True, score=1),
        item("onco", oncologico=True, score=2),
    ]

    fila = ordenar_fila(itens)

    assert [f.solicitacao_id for f in fila] == ["onco", "urgente", "demais"]
    assert [f.camada for f in fila] == [Camada.ONCOLOGICO, Camada.URGENTE, Camada.DEMAIS]
    assert [f.posicao for f in fila] == [1, 2, 3]


def test_urgente_com_score_maior_passa_oncologico():
    """D-112: camadas 1 e 2 formam um bloco só, ordenado pelo score."""
    itens = [
        item("onco", oncologico=True, score=25),
        item("urgente", urgente=True, score=8000),
    ]

    fila = ordenar_fila(itens)

    assert [f.solicitacao_id for f in fila] == ["urgente", "onco"]
    assert [f.camada for f in fila] == [Camada.URGENTE, Camada.ONCOLOGICO]


def test_definir_bloco_junta_camadas_1_e_2():
    assert definir_bloco(Camada.ONCOLOGICO) == definir_bloco(Camada.URGENTE) == 1
    assert definir_bloco(Camada.DEMAIS) == 2


def test_definir_camada_prioriza_oncologico_sobre_urgente():
    assert definir_camada(item("a", oncologico=True, urgente=True)) == Camada.ONCOLOGICO
    assert definir_camada(item("b", urgente=True)) == Camada.URGENTE
    assert definir_camada(item("c")) == Camada.DEMAIS


def test_desempate_por_entrada_mais_antiga_quando_score_empata():
    itens = [
        item("recente", score=50, data=date(2025, 3, 1)),
        item("antiga", score=50, data=date(2024, 6, 1)),
    ]

    fila = ordenar_fila(itens)

    assert [f.solicitacao_id for f in fila] == ["antiga", "recente"]


def test_desempate_final_por_solicitacao_id_quando_score_e_data_empatam():
    itens = [
        item("SOL-30", score=50, data=DATA),
        item("SOL-10", score=50, data=DATA),
        item("SOL-20", score=50, data=DATA),
    ]

    fila = ordenar_fila(itens)

    assert [f.solicitacao_id for f in fila] == ["SOL-10", "SOL-20", "SOL-30"]


def test_solicitacao_id_repetido_levanta_value_error():
    itens = [item("dup"), item("dup", oncologico=True)]

    with pytest.raises(ValueError):
        ordenar_fila(itens)


def test_lista_vazia_devolve_lista_vazia():
    assert ordenar_fila([]) == []


def test_ordenar_fila_nao_modifica_itens_de_entrada():
    itens = [item("b", score=1), item("a", oncologico=True, score=2)]
    copia = [ItemRanking(**vars(i)) for i in itens]

    ordenar_fila(itens)

    assert itens == copia


def test_propriedade_regra_de_ouro_com_300_itens_aleatorios():
    random.seed(42)
    itens: list[ItemRanking] = []
    for i in range(300):
        itens.append(
            item(
                f"SOL-{i:04d}",
                oncologico=random.random() < 0.3,
                urgente=random.random() < 0.4,
                score=round(random.uniform(0, 1000), 2),
                data=DATA + timedelta(days=random.randint(0, 900)),
            )
        )

    fila = ordenar_fila(itens)

    assert [f.posicao for f in fila] == list(range(1, 301))

    # Regra de ouro (I-01): nenhum oncológico abaixo de um paciente da camada 3 (D-112).
    camadas = [f.camada for f in fila]
    ultimo_prioritario = max(
        (i for i, c in enumerate(camadas) if c != Camada.DEMAIS), default=-1
    )
    primeiro_demais = min((i for i, c in enumerate(camadas) if c == Camada.DEMAIS), default=len(camadas))
    assert ultimo_prioritario < primeiro_demais

    # Dentro do bloco prioritário, oncológicos e urgentes se intercalam pelo score.
    bloco = [f for f in fila if f.camada != Camada.DEMAIS]
    assert [f.score_efetivo for f in bloco] == sorted((f.score_efetivo for f in bloco), reverse=True)
    assert {f.camada for f in bloco[:20]} == {Camada.ONCOLOGICO, Camada.URGENTE}
