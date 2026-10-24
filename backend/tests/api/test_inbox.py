"""US-12 · GET /inbox com ListarInbox falso e mock desligado (sem banco)."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.routers.inbox as inbox_router
from app.api.deps import get_listar_inbox
from app.application.listar_inbox import ListarInbox
from app.domain.enums import Classe
from app.domain.models import Motivo
from app.main import app
from tests.application.test_listar_inbox import caso, sol


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(inbox_router, "settings", SimpleNamespace(use_mocks=False))
    em = datetime(2026, 5, 1, 9, 0)
    motivos = {"S1": [Motivo("ps", "PS recorrente", "evento", ref="EVT-1", data=date(2026, 1, 2))]}
    uc, _ = caso(["S1"], [sol("S1", editado_por="reg-1", editado_em=em)],
                 {"S1": Classe.A2}, motivos=motivos, publicada_em=datetime(2026, 10, 24, 10, 0))
    assert isinstance(uc, ListarInbox)
    app.dependency_overrides[get_listar_inbox] = lambda: uc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_inbox_200_no_formato_do_contrato(client):
    r = client.get("/inbox", params={"regulador_id": "reg-9"})
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"total", "itens"} and corpo["total"] == 1
    item = corpo["itens"][0]
    assert set(item) == {"solicitacao_id", "procedimento", "camada", "dias_em_fila",
                         "classe_atual", "classe_sugerida", "motivos", "evento_gatilho",
                         "editado_anteriormente", "criado_em", "previa"}
    assert item["classe_atual"] == "D" and item["classe_sugerida"] == "A2"
    assert item["evento_gatilho"] == "EVT-1"
    assert item["editado_anteriormente"] == {"por": "reg-1", "em": "2026-05-01"}
    assert item["motivos"][0]["ref"] == "EVT-1"
