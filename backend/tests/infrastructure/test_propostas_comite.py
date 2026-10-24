"""US-19 · GET /propostas e POST /propostas/{id}/decidir com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api import deps
from app.api.routers import decisoes as roteador_decisoes
from app.api.routers import inbox as roteador_inbox
from app.api.routers import propostas as roteador
from app.application.gerar_fila import GerarFila
from app.application.gerar_propostas import GerarPropostas
from app.application.publicar_fila import PublicarFila
from app.application.semear_aprendizado import SemearAprendizado
from app.config import settings
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlDecisaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlPropostaRepository,
    SqlRegraRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_aprendido import com_regras
from app.infrastructure.swalis_regras import SwalisRegras
from app.infrastructure.tables import SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial
from app.main import app
from tests.infrastructure.test_resolver_pendencia import carregar

P1 = "PROP-PROC004-ps_recorrente-C-B"  # colecistectomia, C→B (seed P1)
P3 = "PROP-PROC018-sugestao_exagerada-B-C"  # histerectomia rebaixa: descartada (I-01)


@pytest.fixture
def api(session, monkeypatch, tmp_path):
    carregar(session)
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), SwalisRegras(),
                      ExportadorCsv(), settings.ref_date)
    PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
                 lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()
    ref = settings.ref_date
    SemearAprendizado(SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
                      SqlUnidadeDeTrabalho(session), ref).executar()
    GerarPropostas(SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
                   SqlPropostaRepository(session), SqlUnidadeDeTrabalho(session),
                   datetime(ref.year, ref.month, ref.day, tzinfo=timezone.utc)).executar()
    reais = dataclasses.replace(settings, use_mocks=False)
    monkeypatch.setattr(roteador, "settings", reais)
    monkeypatch.setattr(roteador_inbox, "settings", reais)
    monkeypatch.setattr(roteador_decisoes, "settings", reais)
    monkeypatch.setattr(deps, "get_scorer", lambda data=None: SwalisRegras())  # sem LLM: determinístico
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def decidir(api, pid=P1, decisao="aprovar", usuario="comite-01", **extra):
    return api.post(f"/propostas/{pid}/decidir", json={"decisao": decisao, "usuario_id": usuario, **extra})


def test_lista_pendentes_com_casos_de_origem_e_impacto(api):
    r = api.get("/propostas", params={"status": "pendente"})
    assert r.status_code == 200
    ids = {i["proposta_id"] for i in r.json()["itens"]}
    assert P1 in ids and P3 not in ids
    p1 = next(i for i in r.json()["itens"] if i["proposta_id"] == P1)
    assert (p1["classe_de"], p1["classe_para"], p1["direcao"]) == ("C", "B", "subir")
    assert len(p1["casos_origem"]) == p1["n_casos"] and p1["casos_origem"][0]["justificativa"]
    imp = p1["impacto"]
    assert imp["afetados"] > 0 and imp["oncologicos_rebaixados"] == 0 and imp["exemplos"]
    assert p1["procedimento"]


def test_descartada_nao_tem_impacto_e_nao_vai_ao_comite(api):
    r = api.get("/propostas", params={"status": "descartada"})
    p3 = next(i for i in r.json()["itens"] if i["proposta_id"] == P3)
    assert p3["impacto"] is None and p3["motivo_descarte"].startswith("I-01")
    assert decidir(api, P3).status_code == 409


def test_aprovar_cria_a_versao_manda_ao_inbox_e_nao_mexe_na_fila(api, session):
    antes = api.get("/propostas", params={"status": "pendente"}).json()["itens"]
    afetados = next(i for i in antes if i["proposta_id"] == P1)["impacto"]["afetados"]
    inbox_antes = api.get("/inbox").json()["total"]

    r = decidir(api, observacao="Evidência clínica consistente")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert (corpo["status"], corpo["versao"]) == ("aprovada", 1)
    assert corpo["versao_regras"].endswith("+aprendizado-v1") and corpo["enviados_ao_inbox"] > 0
    assert corpo["enviados_ao_inbox"] <= afetados

    regras = SqlRegraRepository(session).listar_ativas()
    assert [(r.regra_id, r.versao) for r in regras] == [(P1, 1)]
    # a classe anterior fica congelada: a fila não muda sem decisão humana (I-04) e o inbox cresce
    session.expire_all()
    congeladas = session.exec(select(SolicitacaoTable).where(
        SolicitacaoTable.procedimento_id == "PROC004", SolicitacaoTable.classe_sistema == "C")).all()
    assert len(congeladas) == corpo["enviados_ao_inbox"]
    inbox = api.get("/inbox")
    assert inbox.json()["total"] == inbox_antes + corpo["enviados_ao_inbox"]
    assert any(i["classe_atual"] == "C" and i["classe_sugerida"] == "B" for i in inbox.json()["itens"])

    aprovada = api.get("/propostas", params={"status": "aprovada"}).json()["itens"][0]
    assert (aprovada["decidida_por"], aprovada["versao"], aprovada["impacto"]) == ("comite-01", 1, None)
    assert aprovada["observacao"] == "Evidência clínica consistente"


def test_o_swalis_passa_a_sugerir_a_classe_nova(api, session):
    sw = SwalisRegras()
    s = next(s for s in SqlSolicitacaoRepository(session).listar() if s.procedimento_id == "PROC004"
             and sw.calcular(s, SqlEventoRepository(session).listar_por_solicitacao(s.solicitacao_id)).classe_sistema.value == "C")
    ev = SqlEventoRepository(session).listar_por_solicitacao(s.solicitacao_id)
    assert decidir(api).status_code == 200
    novo = com_regras(sw, session).calcular(s, ev)
    assert novo.classe_sistema.value == "B" and novo.versao_regras.endswith("+aprendizado-v1")
    assert any(m.sinal == "regra_aprendida" for m in novo.motivos)
    assert novo.prazo_dias == 60


def test_rejeitar_exige_o_motivo_e_registra(api):
    assert decidir(api, decisao="rejeitar").status_code == 422
    assert decidir(api, decisao="rejeitar", observacao="  ").json()["erro"] == "OBSERVACAO_OBRIGATORIA"
    r = decidir(api, decisao="rejeitar", observacao="Amostra pequena para o procedimento")
    assert r.status_code == 200 and r.json()["status"] == "rejeitada"
    rej = api.get("/propostas", params={"status": "rejeitada"}).json()["itens"][0]
    assert (rej["decidida_por"], rej["observacao"]) == ("comite-01", "Amostra pequena para o procedimento")
    assert api.get("/inbox").status_code == 200


def test_decidir_duas_vezes_da_409_e_inexistente_da_404(api):
    assert decidir(api).status_code == 200
    assert decidir(api).json()["erro"] == "PROPOSTA_JA_DECIDIDA"
    assert decidir(api, "PROP-NAO-EXISTE").status_code == 404
    assert decidir(api, P3, decisao="talvez").status_code == 422


def test_gerar_de_novo_nao_recria_a_proposta_decidida(api, session):
    decidir(api)
    ref = settings.ref_date
    GerarPropostas(SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
                   SqlPropostaRepository(session), SqlUnidadeDeTrabalho(session),
                   datetime(ref.year, ref.month, ref.day, tzinfo=timezone.utc)).executar()
    assert P1 not in {i["proposta_id"] for i in api.get("/propostas", params={"status": "pendente"}).json()["itens"]}
    assert api.get("/propostas", params={"status": "aprovada"}).json()["total"] == 1


def test_com_mocks_devolve_o_contrato_fixo(session, monkeypatch):
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=True))
    app.dependency_overrides[get_session] = lambda: session
    try:
        c = TestClient(app)
        assert c.get("/propostas").json()["itens"][0]["impacto"]["afetados"] == 12
        assert c.post("/propostas/X/decidir", json={"decisao": "aprovar", "usuario_id": "u"}).json()["versao"] == 1
    finally:
        app.dependency_overrides.clear()


# ---- reverter (C-14: versionada e reversível) ----

def reverter(api, regra=P1, usuario="comite-02", motivo="Regra ampla demais para o procedimento"):
    return api.post(f"/regras/{regra}/reverter", json={"usuario_id": usuario, "motivo": motivo})


def test_reverter_desativa_a_regra_e_tira_do_inbox_quem_so_estava_la_por_ela(api, session):
    inbox_antes = api.get("/inbox").json()["total"]
    enviados = decidir(api).json()["enviados_ao_inbox"]
    assert api.get("/inbox").json()["total"] == inbox_antes + enviados

    r = reverter(api)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert (corpo["status"], corpo["devolvidos_ao_inbox"]) == ("revertida", enviados)
    assert "aprendizado" not in corpo["versao_regras"]
    assert SqlRegraRepository(session).listar_ativas() == []
    assert api.get("/inbox").json()["total"] == inbox_antes  # voltou ao que era
    session.expire_all()
    assert session.exec(select(SolicitacaoTable).where(SolicitacaoTable.classe_sistema == "C",
                                                       SolicitacaoTable.procedimento_id == "PROC004")).all() == []

    rev = api.get("/propostas", params={"status": "revertida"}).json()["itens"][0]
    assert (rev["proposta_id"], rev["revertida_por"], rev["motivo_reversao"], rev["versao"]) == (
        P1, "comite-02", "Regra ampla demais para o procedimento", 1)
    assert api.get("/propostas", params={"status": "aprovada"}).json()["total"] == 0


def test_o_swalis_volta_a_sugerir_a_classe_antiga(api, session):
    sw = SwalisRegras()
    s = next(s for s in SqlSolicitacaoRepository(session).listar() if s.procedimento_id == "PROC004"
             and sw.calcular(s, SqlEventoRepository(session).listar_por_solicitacao(s.solicitacao_id)).classe_sistema.value == "C")
    ev = SqlEventoRepository(session).listar_por_solicitacao(s.solicitacao_id)
    decidir(api)
    reverter(api)
    assert com_regras(sw, session).calcular(s, ev).classe_sistema.value == "C"


def test_reverter_nao_mexe_em_quem_o_regulador_ja_confirmou(api, session):
    # um paciente afetado é aprovado pelo regulador: a revisão dele vale mesmo se a regra cair
    decidir(api)
    inbox = api.get("/inbox").json()["itens"]
    alvo = next(i["solicitacao_id"] for i in inbox if i["classe_atual"] == "C" and i["classe_sugerida"] == "B")
    assert api.post("/decisoes", json={"solicitacao_id": alvo, "regulador_id": "reg-01", "acao": "aprovar"}).status_code == 200
    reverter(api)
    session.expire_all()
    s = session.get(SolicitacaoTable, alvo)
    assert (s.classe_status, s.classe_confirmada) == ("confirmada", "B")


def test_reverter_exige_motivo_e_nao_repete(api):
    decidir(api)
    assert reverter(api, motivo="  ").json()["erro"] == "OBSERVACAO_OBRIGATORIA"
    assert reverter(api).status_code == 200
    assert reverter(api).json()["erro"] == "REGRA_JA_REVERTIDA"
    assert reverter(api, "PROP-NAO-EXISTE").status_code == 404


def test_regra_nova_depois_da_reversao_abre_a_versao_seguinte(api):
    decidir(api)
    reverter(api)
    assert decidir(api, "PROP-PROC002-piora_funcional-D-C").json()["versao"] == 2  # nunca reaproveita número


def test_proposta_revertida_nao_volta_ao_gerar_de_novo(api, session):
    decidir(api)
    reverter(api)
    ref = settings.ref_date
    GerarPropostas(SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
                   SqlPropostaRepository(session), SqlUnidadeDeTrabalho(session),
                   datetime(ref.year, ref.month, ref.day, tzinfo=timezone.utc)).executar()
    assert P1 not in {i["proposta_id"] for i in api.get("/propostas", params={"status": "pendente"}).json()["itens"]}
