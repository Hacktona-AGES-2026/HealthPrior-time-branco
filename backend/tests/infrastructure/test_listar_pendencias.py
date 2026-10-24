"""US-06 · GET /pendencias com o dataset real (precisa do Postgres de teste)."""
import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlmodel import text

from app.api.routers import pendencias as roteador
from app.application.carga_inicial import CargaInicial
from app.application.detectar_bloqueantes import DetectarBloqueantes
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlPendenciaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.main import app


def carregar(session):
    """A carga como o CLI faz: gera as 164 pendências abertas (108 não bloqueantes + 56 bloqueantes)."""
    sol, ev, cor, pen = (SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                         SqlCorrecaoRepository(session), SqlPendenciaRepository(session))
    CargaInicial(LeitorDataset(settings.data_dir), SqlCargaRepository(session), Normalizar(sol, cor),
                 SqlUnidadeDeTrabalho(session), RecalcularFlags(sol, ev, cor),
                 DetectarInconsistencias(sol, ev, pen, settings.ref_date),
                 DetectarBloqueantes(sol, ev, pen, settings.ref_date)).executar()


@pytest.fixture
def api(session, monkeypatch):
    """Cliente com o banco de teste e a rota real (HP_USE_MOCKS=false)."""
    carregar(session)
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=False))
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def listar(api, **params):
    resposta = api.get("/pendencias", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def por_solicitacao(corpo, sol_id, regra):
    (item,) = [i for i in corpo["itens"] if i["solicitacao_id"] == sol_id and i["regra"] == regra]
    return item


def test_por_padrao_lista_as_abertas(api):
    corpo = listar(api)

    assert corpo["total"] == len(corpo["itens"]) == 164
    assert {i["status"] for i in corpo["itens"]} == {"aberta"}


def test_formato_do_contrato(api):
    item = por_solicitacao(listar(api), "SOL-2025-00053", "PRE-10")  # "NUMERO NAO EXISTE"

    assert set(item) == {"pendencia_id", "solicitacao_id", "regra", "titulo", "bloqueante",
                         "evidencias", "acao_sugerida", "status", "aberta_em"}
    assert (item["titulo"], item["bloqueante"], item["aberta_em"]) == ("Contato perdido", False, "2026-10-23")
    assert item["acao_sugerida"] and item["pendencia_id"].startswith("PEN-")
    assert set(item["evidencias"][0]) == {"fonte", "ref", "texto"}


def test_filtro_bloqueante(api):
    assert listar(api, bloqueante="true")["total"] == 56
    assert listar(api, bloqueante="false")["total"] == 108
    assert all(i["bloqueante"] for i in listar(api, bloqueante="true")["itens"])


def test_bloqueantes_vem_primeiro(api):
    flags = [i["bloqueante"] for i in listar(api)["itens"]]

    assert flags == sorted(flags, reverse=True) and flags[0] is True and flags[-1] is False


def test_ordem_e_estavel(api):
    assert listar(api) == listar(api)


@pytest.mark.parametrize("regra, total", [
    ("PRE-10", 39), ("PRE-11", 28), ("PRE-12", 23), ("PRE-13", 18),
    ("PRE-20", 22), ("PRE-21", 1), ("PRE-22", 2), ("PRE-23", 10), ("PRE-24", 9), ("PRE-25", 12),
    ("PRE-14", 0), ("PRE-99", 0),  # PRE-14 só alerta; regra desconhecida não dá erro
])
def test_filtro_por_regra(api, regra, total):
    corpo = listar(api, regra=regra)

    assert corpo["total"] == total
    assert {i["regra"] for i in corpo["itens"]} <= {regra}


def test_fontes_contraditorias_trazem_as_duas_evidencias(api):
    # SOL-2026-00305: o call center diz "desistiu"; a observação diz "operou pelo convênio"
    item = por_solicitacao(listar(api, regra="PRE-25"), "SOL-2026-00305", "PRE-25")

    assert item["bloqueante"] is True and len(item["evidencias"]) == 2
    por_fonte = {e["fonte"]: e for e in item["evidencias"]}
    assert por_fonte["observacoes"]["texto"] == "Familiar informa que paciente operou pelo convenio."
    assert por_fonte["evento"]["ref"].startswith("EVT-")
    assert por_fonte["evento"]["texto"] == "Pct informa que nao deseja mais realizar a cirurgia."


def test_toda_pendencia_de_fontes_contraditorias_tem_as_duas_fontes(api):
    itens = listar(api, regra="PRE-25")["itens"]

    assert itens and all({e["fonte"] for e in i["evidencias"]} == {"evento", "observacoes"} for i in itens)


def test_evidencia_de_origem_em_cada_caso(api):
    corpo = listar(api)

    cancer = por_solicitacao(corpo, "SOL-2026-00757", "PRE-12")  # D37.4 com biópsia positiva
    assert {e["fonte"] for e in cancer["evidencias"]} == {"evento", "cid"}
    assert next(e for e in cancer["evidencias"] if e["fonte"] == "evento")["ref"].startswith("EVT-")
    acs = por_solicitacao(corpo, "SOL-2026-00059", "PRE-11")
    assert acs["evidencias"][0] == {"fonte": "observacoes", "ref": None, "texto": "PCT NAO POSSUI TELEFONE FIXO. CONTATO VIA ACS."}
    diabetes = por_solicitacao(corpo, "SOL-2026-00444", "PRE-13")
    assert "Diabetes nao consta no cadastro" in diabetes["evidencias"][0]["texto"]


def test_duplicata_mostra_as_duas_solicitacoes(api):
    item = por_solicitacao(listar(api, regra="PRE-20"), "SOL-2025-00348", "PRE-20")  # PAC-00151

    assert [e["ref"] for e in item["evidencias"]] == ["SOL-2025-00290", "SOL-2025-00348"]
    assert "SOL-2025-00290" in item["acao_sugerida"]


def test_evento_orfao_cita_o_evento_e_o_id_inexistente(api):
    item = por_solicitacao(listar(api, regra="PRE-24"), "SOL-2023-00941", "PRE-24")  # EVT-000287

    assert item["evidencias"][0]["ref"] == "EVT-000287"
    assert "SOL-2023-00941" in item["acao_sugerida"]


def test_filtros_combinados(api):
    corpo = listar(api, regra="PRE-10", bloqueante="false")

    assert corpo["total"] == 39
    assert listar(api, regra="PRE-10", bloqueante="true")["total"] == 0


def test_filtro_de_status(api, session):
    session.exec(text("update pendencias set status='resolvida', resolvido_por='adm-01' "
                      "where solicitacao_id='SOL-2025-00053' and regra='PRE-10'"))
    session.exec(text("update pendencias set status='descartada' "
                      "where solicitacao_id='SOL-2026-00059' and regra='PRE-11'"))
    session.commit()

    assert listar(api)["total"] == 162  # a resolvida e a descartada saem da lista padrão
    resolvidas = listar(api, status="resolvida")
    assert [i["solicitacao_id"] for i in resolvidas["itens"]] == ["SOL-2025-00053"]
    assert resolvidas["itens"][0]["status"] == "resolvida"
    assert [i["solicitacao_id"] for i in listar(api, status="descartada")["itens"]] == ["SOL-2026-00059"]


def test_status_invalido_da_422(api):
    assert api.get("/pendencias", params={"status": "qualquer"}).status_code == 422


def test_listar_nao_altera_nada(api, session):
    antes = session.exec(text("select count(*), count(*) filter (where status='aberta') from pendencias")).one()

    listar(api)
    listar(api, bloqueante="true")

    assert session.exec(text("select count(*), count(*) filter (where status='aberta') from pendencias")).one() == antes


def test_com_mocks_ligados_devolve_o_contrato_fixo(session, monkeypatch):
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=True))
    app.dependency_overrides[get_session] = lambda: session
    try:
        corpo = TestClient(app).get("/pendencias").json()
    finally:
        app.dependency_overrides.clear()

    assert corpo["total"] == 1 and corpo["itens"][0]["pendencia_id"] == "PEN-0001"
