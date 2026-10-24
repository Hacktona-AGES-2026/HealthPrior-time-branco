"""US-20 · GET /fila com ListarFila falso e mock desligado (sem banco)."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.routers.fila as fila_router
from app.api.deps import get_listar_fila
from app.application.listar_fila import ListarFila
from app.domain.enums import ClasseStatus
from app.domain.models import LinhaFila, Solicitacao
from app.main import app
from tests.application.test_listar_fila import FilaFalsa, SolicitacoesFalsas


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(fila_router, "settings", SimpleNamespace(use_mocks=False))
    linhas = [LinhaFila(solicitacao_id="SOL-1", posicao=1, justificativa="Camada 2 ...",
                        camada=2, classe="B", pct_prazo_consumido=10.0, dias_em_fila=30,
                        score_efetivo=1.0, editado_manualmente=False, versao_regras="regras-1")]
    sols = [Solicitacao(solicitacao_id="SOL-1", paciente_id="PAC-1", procedimento_id="P-1",
                        cid_principal="C61", data_entrada_fila=date(2025, 1, 1),
                        procedimento="Prostatectomia", especialidade="Urologia",
                        classe_status=ClasseStatus.CONFIRMADA)]
    caso = ListarFila(FilaFalsa(linhas, datetime(2026, 10, 24, 10, 0)),
                      SolicitacoesFalsas(sols))
    app.dependency_overrides[get_listar_fila] = lambda: caso
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_fila_200_no_formato_do_contrato(client):
    r = client.get("/fila")
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"versao_regras", "gerada_em", "publicada", "total", "itens"}
    assert corpo["versao_regras"] == "regras-1"
    assert corpo["publicada"] is True
    assert corpo["total"] == 1
    item = corpo["itens"][0]
    assert item["solicitacao_id"] == "SOL-1"
    assert item["classe_status"] == "confirmada"
    assert item["cid"] == "C61"
    assert item["procedimento"] == "Prostatectomia"
    assert item["alertas"] == []
    assert item["resumo_justificativa"] == "Camada 2 ..."


def test_get_fila_filtro_por_query(client):
    r = client.get("/fila", params={"camada": 1})
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["itens"] == []


def test_page_zero_422(client):
    r = client.get("/fila", params={"page": 0})
    assert r.status_code == 422
    assert r.json()["erro"] == "PAGINACAO_INVALIDA"


def test_page_size_acima_de_200_e_limitado(client):
    assert client.get("/fila", params={"page_size": 201}).status_code == 200


def test_mock_quando_use_mocks_ligado(monkeypatch):
    monkeypatch.setattr(fila_router, "settings", SimpleNamespace(use_mocks=True))
    r = TestClient(app).get("/fila")
    assert r.status_code == 200
    assert r.json()["versao_regras"] == "stub-0"
