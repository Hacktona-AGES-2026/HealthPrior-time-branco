"""Prévia da decisão: posição, % do prazo e score estimados batem com a fila refeita depois da decisão."""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone

import pytest

from app.application.montar_fila import montar_fila
from app.application.previa import prever_decisao
from app.config import settings
from app.domain.decisao import aplicar_decisao
from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado
from app.domain.errors import OncologicoRebaixadoError
from app.domain.models import Evento
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.swalis_regras import SwalisRegras

REF = settings.ref_date
SCORER = SwalisRegras()  # sem LLM e sem fatores: determinístico


@pytest.fixture(scope="module")
def dataset():
    return carregar_do_csv(settings.data_dir)


def _cenario(dataset, sid, evento=None):
    sols, eventos = copy.deepcopy(dataset)
    if evento:
        eventos.setdefault(sid, []).append(evento)
    linhas = montar_fila(sols, eventos, SCORER, REF)
    s = next(x for x in sols if x.solicitacao_id == sid)
    res = SCORER.calcular(s, eventos.get(sid, []))
    entradas = {x.solicitacao_id: x.data_entrada_fila for x in sols}
    return sols, eventos, linhas, s, res, entradas


def _real(sols, eventos, s, res, acao, classe=None, score=None):
    aplicar_decisao(s, acao, res.classe_sistema, classe, score, MotivoCodificado.OUTRO, "R",
                    datetime(REF.year, REF.month, REF.day, tzinfo=timezone.utc))
    return next(l for l in montar_fila(sols, eventos, SCORER, REF) if l.solicitacao_id == s.solicitacao_id)


def test_previa_de_aprovar_bate_com_a_fila_refeita(dataset):
    # SOL-2026-00239 (hérnia, C) + biópsia positiva -> sugere A2
    ev = Evento("EVT-T1", "SOL-2026-00239", "P", date(2026, 10, 20), "biopsia", "positivo", None, "AP")
    sols, eventos, linhas, s, res, entradas = _cenario(dataset, "SOL-2026-00239", ev)
    assert res.classe_sistema is Classe.A2
    p = prever_decisao(s, res, linhas, entradas, REF, AcaoDecisao.APROVAR)
    real = _real(sols, eventos, s, res, AcaoDecisao.APROVAR)
    assert (p.classe.value, p.posicao_estimada, p.pct_prazo_consumido, p.score) == (
        real.classe, real.posicao, real.pct_prazo_consumido, real.score_efetivo)
    assert p.posicao_atual == next(l.posicao for l in linhas if l.solicitacao_id == s.solicitacao_id)


@pytest.mark.parametrize("classe", [Classe.A1, Classe.B, Classe.D])
def test_previa_de_editar_bate_com_a_fila_refeita(dataset, classe):
    sols, eventos, linhas, s, res, entradas = _cenario(dataset, "SOL-2023-00060")
    p = prever_decisao(s, res, linhas, entradas, REF, AcaoDecisao.EDITAR, classe=classe)
    real = _real(sols, eventos, s, res, AcaoDecisao.EDITAR, classe=classe)
    assert (p.classe, p.posicao_estimada, p.score) == (classe, real.posicao, real.score_efetivo)


def test_previa_nao_altera_a_solicitacao(dataset):
    sols, eventos, linhas, s, res, entradas = _cenario(dataset, "SOL-2023-00060")
    antes = copy.deepcopy(s)
    prever_decisao(s, res, linhas, entradas, REF, AcaoDecisao.EDITAR, classe=Classe.A1)
    assert s == antes


def test_previa_recusa_oncologico_para_d(dataset):
    sols, eventos, linhas, s, res, entradas = _cenario(dataset, "SOL-2025-00149")  # C61
    with pytest.raises(OncologicoRebaixadoError):
        prever_decisao(s, res, linhas, entradas, REF, AcaoDecisao.EDITAR, classe=Classe.D)
