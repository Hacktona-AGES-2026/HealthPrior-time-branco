"""US-10 · GET /fila/export e POST /admin/publicar-fila com dependências trocadas (sem banco)."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_exportar_fila_publicada, get_publicar_fila
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


def _publicar(publicada):
    res = SimpleNamespace(publicada=publicada, total=2, por_camada={1: 2}, versao_regras="v1",
                          saida_verificador="saida")
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
                        "versao_regras": "v1", "saida_verificador": "saida"}
