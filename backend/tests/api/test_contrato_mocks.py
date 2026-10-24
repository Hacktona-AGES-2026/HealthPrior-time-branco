"""Garante que os endpoints do contrato respondem no formato de docs/user-stories.md §5."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_fila():
    r = client.get("/fila")
    assert r.status_code == 200
    assert r.json()["itens"][0]["solicitacao_id"] == "SOL-2023-00010"


def test_detalhe():
    assert client.get("/solicitacoes/SOL-2023-00010").json()["camada"] == 1


def test_inbox():
    assert client.get("/inbox").json()["itens"][0]["classe_sugerida"] == "B"


def test_decisao():
    r = client.post("/decisoes", json={"solicitacao_id": "SOL-2023-00060", "regulador_id": "reg-01",
                                       "acao": "aprovar"})
    assert r.status_code == 200


def test_evento():
    r = client.post("/eventos", json={"solicitacao_id": "SOL-2023-00060", "data_evento": "2026-10-23",
                                      "tipo_evento": "pronto_socorro", "resultado": "observacao"})
    assert r.status_code == 201


def test_pendencias():
    assert client.get("/pendencias").json()["itens"][0]["regra"] == "PRE-25"
    r = client.post("/pendencias/PEN-0001/resolver",
                    json={"resolucao": "confirmar_saida", "usuario_id": "adm-01"})
    assert r.status_code == 200


def test_nao_implementado_vira_501():
    assert client.post("/admin/carga").status_code == 501
