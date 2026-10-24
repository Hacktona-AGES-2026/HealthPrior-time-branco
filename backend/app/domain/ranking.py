"""Trava da regra de ouro (C-11, US-08).

Regra de ouro (I-01): nenhum paciente oncológico pode ficar abaixo de um
paciente sem urgência clínica. Cada paciente recebe uma camada (1 = oncológico,
2 = urgente não oncológico, 3 = demais), mas a fila tem só dois blocos (D-108,
revisa D-06): o bloco prioritário junta as camadas 1 e 2, e o bloco das demais
(camada 3) vem abaixo e nunca invade o de cima. Assim um urgente pode passar um
oncológico, o que a regra permite: todo sinal da camada 2 também é urgência para
o verificador oficial. Dentro de cada bloco, a ordem é pelo score efetivo (maior
primeiro), depois pela entrada mais antiga e, por fim, pelo identificador da
solicitação, de modo que a ordem seja sempre determinística.
"""
from __future__ import annotations

from app.domain.enums import Camada
from app.domain.models import ItemFila, ItemRanking


def definir_camada(item: ItemRanking) -> Camada:
    """Classifica o item na camada da trava.

    Oncológico vai para a camada 1; senão, urgente vai para a camada 2; os
    demais vão para a camada 3.
    """
    if item.oncologico:
        return Camada.ONCOLOGICO
    if item.urgente:
        return Camada.URGENTE
    return Camada.DEMAIS


def definir_bloco(camada: Camada) -> int:
    """Bloco de ordenação: 1 = prioritário (camadas 1 e 2), 2 = demais (camada 3)."""
    return 2 if camada == Camada.DEMAIS else 1


def ordenar_fila(itens: list[ItemRanking]) -> list[ItemFila]:
    """Ordena a fila aplicando a trava da regra de ouro (I-01).

    Chave de ordenação: bloco crescente, score efetivo decrescente, data de
    entrada na fila crescente e solicitacao_id crescente. Devolve as posições
    1..n sem buracos. Não altera os itens recebidos.

    Levanta ValueError se houver solicitacao_id repetido.
    """
    ids_vistos: set[str] = set()
    for item in itens:
        if item.solicitacao_id in ids_vistos:
            raise ValueError(f"solicitacao_id repetido na fila: {item.solicitacao_id!r}")
        ids_vistos.add(item.solicitacao_id)

    ordenados = sorted(
        itens,
        key=lambda item: (
            definir_bloco(definir_camada(item)),
            -item.score_efetivo,
            item.data_entrada_fila,
            item.solicitacao_id,
        ),
    )
    return [
        ItemFila(
            posicao=posicao,
            solicitacao_id=item.solicitacao_id,
            camada=definir_camada(item),
            score_efetivo=item.score_efetivo,
        )
        for posicao, item in enumerate(ordenados, start=1)
    ]
