"""Importar solicitações por CSV com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select

from app.api import deps
from app.api.routers import importacao as roteador
from app.application.gerar_fila import GerarFila
from app.application.publicar_fila import PublicarFila
from app.config import settings
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.importacao_csv import OBRIGATORIAS
from app.infrastructure.repositories import (
    SqlEventoRepository,
    SqlFilaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import SwalisRegras
from app.infrastructure.tables import CorrecaoTable, PendenciaTable, SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial
from app.main import app
from tests.infrastructure.test_resolver_pendencia import carregar

CAB = ",".join(OBRIGATORIAS) + ",justificativa_clinica,observacoes,idade,sexo"


def linha(sid, nome="Paciente Importado", proc="PROC004", cid="K80.2", just="Colecistite calculosa", obs="", idade=55):
    return f"{sid},PAC-{sid},{nome},{proc},{cid},2026-10-01,{just},{obs},{idade},F"


@pytest.fixture
def api(session, tmp_path, monkeypatch):
    carregar(session)
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), SwalisRegras(),
                      ExportadorCsv(), settings.ref_date)
    PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
                 lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=False))
    monkeypatch.setattr(deps, "settings", dataclasses.replace(settings, output_dir=tmp_path))
    monkeypatch.setattr(deps, "get_scorer", lambda data=None: SwalisRegras(ref_date=data))
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def importar(c, texto, **params):
    return c.post("/importacao/solicitacoes", content=texto.encode("utf-8"), params=params,
                  headers={"content-type": "text/csv"})


def total(session, modelo=SolicitacaoTable):
    session.expire_all()
    return session.exec(select(func.count()).select_from(modelo)).one()


def test_modelo_baixavel(api):
    r = api.get("/importacao/modelo.csv")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0].startswith("solicitacao_id,paciente_id")


def test_uma_linha_entra_passa_pelo_pipeline_e_aparece_na_fila(api, session):
    antes, fila_antes = total(session), len(SqlFilaRepository(session).obter_publicada())
    r = importar(api, f"{CAB}\n{linha('SOL-IMP-1')}\n")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert (corpo["lidas"], corpo["novas"], corpo["ja_existentes"], corpo["erros"]) == (1, 1, [], [])
    assert corpo["fila_publicada"] is True and corpo["total_fila"] == fila_antes + 1
    assert total(session) == antes + 1
    s = SqlSolicitacaoRepository(session).obter("SOL-IMP-1")
    assert s.nome_norm == "paciente importado" and s.cid_norm == "K802"  # normalizou como na carga
    assert s.procedimento == "Colecistectomia videolaparoscopica" and s.status_fila.value == "ativa"
    assert "SOL-IMP-1" in {l.solicitacao_id for l in SqlFilaRepository(session).obter_publicada()}


def test_varias_linhas_e_uma_que_ja_suspende_pelo_texto(api, session):
    texto = (f"{CAB}\n{linha('SOL-IMP-1')}\n{linha('SOL-IMP-2', 'Outra Pessoa')}\n"
             f"{linha('SOL-IMP-3', 'Terceira Pessoa', obs='Familiar informa que paciente operou pelo convenio.')}\n")
    corpo = importar(api, texto).json()
    assert (corpo["lidas"], corpo["novas"]) == (3, 3) and corpo["suspensas"] == 1
    sus = SqlSolicitacaoRepository(session).obter("SOL-IMP-3")
    assert sus.status_fila.value == "suspensa" and sus.motivo_status == "PRE-22"
    session.expire_all()
    assert session.exec(select(func.count()).select_from(PendenciaTable).where(
        PendenciaTable.solicitacao_id == "SOL-IMP-3", PendenciaTable.bloqueante)).one() >= 1
    assert "SOL-IMP-3" not in {l.solicitacao_id for l in SqlFilaRepository(session).obter_publicada()}


def test_erro_em_qualquer_linha_nao_grava_nada(api, session):
    antes = total(session)
    r = importar(api, f"{CAB}\n{linha('SOL-IMP-1')}\n{linha('SOL-IMP-2', proc='PROC999')}\n")
    assert r.status_code == 422
    corpo = r.json()
    assert corpo["novas"] == 0 and corpo["erros"][0]["linha"] == 3 and corpo["erros"][0]["campo"] == "procedimento_id"
    assert total(session) == antes


def test_quem_ja_existe_e_ignorado_nunca_sobrescrito(api, session):
    existente = session.exec(select(SolicitacaoTable).limit(1)).one()
    nome_original = existente.nome_paciente
    corpo = importar(api, f"{CAB}\n{linha(existente.solicitacao_id, 'NOME TROCADO')}\n{linha('SOL-IMP-9')}\n").json()
    assert corpo["novas"] == 1 and corpo["ja_existentes"] == [existente.solicitacao_id]
    session.expire_all()
    assert session.get(SolicitacaoTable, existente.solicitacao_id).nome_paciente == nome_original  # I-10
    # repetir o mesmo arquivo não duplica nada
    de_novo = importar(api, f"{CAB}\n{linha('SOL-IMP-9')}\n").json()
    assert de_novo["novas"] == 0 and de_novo["ja_existentes"] == ["SOL-IMP-9"] and de_novo["fila_publicada"] is None


def test_sem_republicar_e_arquivo_em_latin1(api, session):
    fila_antes = len(SqlFilaRepository(session).obter_publicada())
    texto = f"{CAB}\n{linha('SOL-IMP-5', 'José da Conceição')}\n"
    r = api.post("/importacao/solicitacoes", content=texto.encode("latin-1"), params={"publicar": "false"})
    assert r.status_code == 200 and r.json()["fila_publicada"] is None
    assert len(SqlFilaRepository(session).obter_publicada()) == fila_antes  # a fila só muda ao republicar
    assert SqlSolicitacaoRepository(session).obter("SOL-IMP-5").nome_paciente == "José da Conceição"


def test_com_mocks_devolve_o_contrato_fixo(session, monkeypatch):
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=True))
    app.dependency_overrides[get_session] = lambda: session
    try:
        r = TestClient(app).post("/importacao/solicitacoes", content=b"x")
        assert r.status_code == 200 and r.json()["novas"] == 2
    finally:
        app.dependency_overrides.clear()
