"""US-07 · POST /pendencias/{id}/resolver pela composição real (precisa do Postgres de teste)."""
import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api import deps
from app.api.routers import pendencias as roteador
from app.config import settings
from app.infrastructure.db import get_session
from app.infrastructure.swalis_stub import SwalisStub
from app.infrastructure.tables import PendenciaTable
from app.main import app

from tests.infrastructure.test_resolver_pendencia import carregar


@pytest.fixture
def api(session, tmp_path, monkeypatch):
    """Back real (mocks desligados), com o banco de teste, o SWALIS stub e a saída em tmp_path."""
    carregar(session)
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=False))
    monkeypatch.setattr(deps, "settings", dataclasses.replace(settings, output_dir=tmp_path))
    monkeypatch.setattr(deps, "get_scorer", lambda: SwalisStub())
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def id_da(session, sol_id, regra):
    return session.exec(select(PendenciaTable.pendencia_id).where(
        PendenciaTable.solicitacao_id == sol_id, PendenciaTable.regra == regra)).one()


def resolver(api, session, sol_id, regra, **corpo):
    corpo.setdefault("usuario_id", "adm-01")
    return api.post(f"/pendencias/{id_da(session, sol_id, regra)}/resolver", json=corpo)


def test_confirmar_saida_devolve_o_contrato(api, session):
    r = resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="confirmar_saida",
                 observacao="Confirmado por telefone.")

    assert r.status_code == 200
    assert r.json() == {"status_fila": "removida", "fila_publicada": True}


def test_a_resolvida_sai_da_lista_de_abertas_e_aparece_em_resolvidas(api, session):
    abertas = api.get("/pendencias").json()["total"]

    resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="reativar")

    assert api.get("/pendencias").json()["total"] == abertas - 1
    resolvidas = api.get("/pendencias", params={"status": "resolvida"}).json()["itens"]
    assert [i["solicitacao_id"] for i in resolvidas] == ["SOL-2024-00076"]
    # a lista de resolvidas diz quem, quando e como (C-06)
    assert (resolvidas[0]["resolvido_por"], resolvidas[0]["resolucao"]) == ("adm-01", "reativar")
    assert resolvidas[0]["resolvido_em"] is not None


def test_observacao_e_opcional_fora_de_confirmar_saida(api, session):
    r = resolver(api, session, "SOL-2026-00305", "PRE-25", resolucao="descartar")

    assert r.status_code == 200 and r.json()["status_fila"] == "ativa"


def test_fundir_com_pela_api(api, session):
    r = resolver(api, session, "SOL-2025-00348", "PRE-20", resolucao="fundir", fundir_com="SOL-2025-00290")

    assert r.status_code == 200 and r.json() == {"status_fila": "removida", "fila_publicada": True}


def test_evento_orfao_devolve_status_fila_nulo(api, session):
    r = resolver(api, session, "SOL-2023-00941", "PRE-24", resolucao="descartar")

    assert r.status_code == 200
    assert r.json() == {"status_fila": None, "fila_publicada": True}


def test_pendencia_inexistente_da_404(api):
    r = api.post("/pendencias/PEN-9999/resolver", json={"resolucao": "descartar", "usuario_id": "adm-01"})

    assert r.status_code == 404 and r.json()["erro"] == "PENDENCIA_NAO_ENCONTRADA"


def test_resolver_duas_vezes_da_409(api, session):
    resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="reativar")

    r = resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="descartar", usuario_id="adm-02")

    assert r.status_code == 409 and r.json()["erro"] == "PENDENCIA_JA_RESOLVIDA"
    assert "adm-01" in r.json()["mensagem"]


def test_confirmar_saida_sem_observacao_da_422(api, session):
    r = resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="confirmar_saida")

    assert r.status_code == 422 and r.json()["erro"] == "OBSERVACAO_OBRIGATORIA"


def test_resolucao_que_a_regra_nao_aceita_da_422(api, session):
    r = resolver(api, session, "SOL-2023-00941", "PRE-24", resolucao="confirmar_saida", observacao="x")

    assert r.status_code == 422 and r.json()["erro"] == "RESOLUCAO_INVALIDA"


def test_resolucao_fora_do_enum_da_422(api, session):
    r = resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="apagar")

    assert r.status_code == 422


def test_usuario_e_obrigatorio(api, session):
    r = api.post(f"/pendencias/{id_da(session, 'SOL-2024-00076', 'PRE-23')}/resolver", json={"resolucao": "reativar"})

    assert r.status_code == 422


def test_erro_nao_deixa_nada_pela_metade(api, session):
    resolver(api, session, "SOL-2024-00076", "PRE-23", resolucao="confirmar_saida")  # 422 por falta de observação

    session.expire_all()
    p = session.exec(select(PendenciaTable).where(PendenciaTable.solicitacao_id == "SOL-2024-00076",
                                                  PendenciaTable.regra == "PRE-23")).one()
    assert (p.status, p.resolvido_por) == ("aberta", None)


def test_com_mocks_ligados_devolve_o_contrato_fixo(session, monkeypatch):
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=True))
    app.dependency_overrides[get_session] = lambda: session
    try:
        r = TestClient(app).post("/pendencias/PEN-0001/resolver",
                                 json={"resolucao": "confirmar_saida", "usuario_id": "adm-01"})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200 and r.json() == {"status_fila": "removida", "fila_publicada": True}
