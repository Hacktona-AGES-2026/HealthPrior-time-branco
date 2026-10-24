"""Prévia da decisão (US-13/14): % do prazo, score e posição que o paciente teria se o regulador
aprovasse, editasse ou mantivesse — antes de gravar nada.

Usa o mesmo código da decisão e da fila numa cópia da solicitação (`aplicar_decisao` +
`classe_e_score_efetivos`) e a mesma chave de ordenação da trava (bloco, score, entrada, id).
A camada não depende da classe e os outros pacientes não mudam, então a posição é a que a próxima
publicação daria (salvo se o verificador reprovar).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.application.montar_fila import classe_e_score_efetivos
from app.domain.decisao import aplicar_decisao
from app.domain.enums import AcaoDecisao, Camada, Classe, MotivoCodificado
from app.domain.models import LinhaFila, ResultadoScore, Solicitacao
from app.domain.ranking import definir_bloco


@dataclass
class Previa:
    classe: Classe
    pct_prazo_consumido: float
    score: float
    posicao_atual: int | None
    posicao_estimada: int | None


def _chave(camada: int, score: float, entrada: date, solicitacao_id: str) -> tuple:
    return (definir_bloco(Camada(camada)), -score, entrada, solicitacao_id)


def prever_decisao(s: Solicitacao, res: ResultadoScore, linhas: list[LinhaFila],
                   entradas: dict[str, date], ref_date: date, acao: AcaoDecisao,
                   classe: Classe | None = None, score: float | None = None) -> Previa:
    """`linhas`: fila publicada; `entradas`: data de entrada de cada solicitação da fila.

    Levanta os mesmos erros da decisão real (ex.: OncologicoRebaixadoError).
    """
    simulada = copy.deepcopy(s)
    editado_em = datetime(ref_date.year, ref_date.month, ref_date.day, tzinfo=timezone.utc)
    motivo = None if acao == AcaoDecisao.APROVAR else MotivoCodificado.OUTRO
    aplicar_decisao(simulada, acao, res.classe_sistema, classe, score, motivo, "previa", editado_em)
    nova_classe, novo_score, pct = classe_e_score_efetivos(simulada, res, ref_date)

    propria = next((l for l in linhas if l.solicitacao_id == s.solicitacao_id), None)
    if propria is None:  # fora da fila publicada (suspensa, ou fila ainda não publicada)
        return Previa(nova_classe, pct, novo_score, None, None)
    minha = _chave(propria.camada, novo_score, s.data_entrada_fila, s.solicitacao_id)
    a_frente = sum(
        1 for l in linhas
        if l.solicitacao_id != s.solicitacao_id
        and _chave(l.camada, l.score_efetivo, entradas.get(l.solicitacao_id, date.max),
                   l.solicitacao_id) < minha)
    return Previa(nova_classe, pct, novo_score, propria.posicao, a_frente + 1)
