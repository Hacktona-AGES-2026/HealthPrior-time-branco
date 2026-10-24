"""US-10/16 · GET /fila/export, POST /admin/publicar-fila e /admin/atualizacao-diaria com
dependências trocadas (sem banco)."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_atualizacao_diaria, get_exportar_fila_publicada, get_publicar_fila
from app.domain.errors import FilaNaoPublicadaError
from app.main import app


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_export_sem_fila_publicada_409(client):
    class Vazio:
        def executar(self):
            raise FilaNaoPublicadaError()

    app.dependency_overrides[get_exportar_fila_publicada] = lambda: Vazio()
    r = client.get("/fila/export")
    assert r.status_code == 409
    assert r.json()["erro"] == "FILA_NAO_PUBLICADA"
    assert "mensagem" in r.json()


def test_export_com_fila_200_csv(client, tmp_path):
    arq = tmp_path / "fila_publicada.csv"
    arq.write_text("solicitacao_id,posicao,justificativa\nSOL-1,1,j\n")
    app.dependency_overrides[get_exportar_fila_publicada] = lambda: SimpleNamespace(
        executar=lambda: arq)
    r = client.get("/fila/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "SOL-1" in r.text


def _resultado(publicada, data=date(2026, 10, 23)):
    return SimpleNamespace(publicada=publicada, total=2, por_camada={1: 2}, versao_regras="v1",
                           saida_verificador="saida", data_referencia=data)


def _publicar(publicada):
    res = _resultado(publicada)
    return SimpleNamespace(executar=lambda: res)


def test_publicar_verificador_falhou_422(client):
    app.dependency_overrides[get_publicar_fila] = lambda: _publicar(False)
    r = client.post("/admin/publicar-fila")
    assert r.status_code == 422
    assert r.json()["publicada"] is False


def test_publicar_ok_200(client):
    app.dependency_overrides[get_publicar_fila] = lambda: _publicar(True)
    r = client.post("/admin/publicar-fila")
    assert r.status_code == 200
    assert r.json() == {"publicada": True, "total": 2, "por_camada": {"1": 2},
                        "versao_regras": "v1", "saida_verificador": "saida",
                        "data_referencia": "2026-10-23"}


class AtualizacaoFalsa:
    def __init__(self, publicada=True):
        self.publicada = publicada
        self.datas = []

    def executar(self, data=None):
        self.datas.append(data)
        return _resultado(self.publicada, data or date(2026, 10, 24))


def test_atualizacao_diaria_sem_data_avanca(client):
    caso = AtualizacaoFalsa()
    app.dependency_overrides[get_atualizacao_diaria] = lambda: caso
    r = client.post("/admin/atualizacao-diaria")
    assert r.status_code == 200
    assert r.json()["data_referencia"] == "2026-10-24" and r.json()["publicada"] is True
    assert caso.datas == [None]


def test_atualizacao_diaria_com_data_e_verificador_falhou_422(client):
    caso = AtualizacaoFalsa(publicada=False)
    app.dependency_overrides[get_atualizacao_diaria] = lambda: caso
    r = client.post("/admin/atualizacao-diaria", params={"data": "2026-11-01"})
    assert r.status_code == 422
    assert r.json()["publicada"] is False
    assert caso.datas == [date(2026, 11, 1)]
