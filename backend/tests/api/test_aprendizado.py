"""US-18 · POST /aprendizado/gerar-propostas: mock e caso de uso falso (sem banco)."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.routers.aprendizado as router
from app.api.deps import get_gerar_propostas, get_nomes_procedimentos
from app.application.gerar_propostas import ResultadoGeracao
from app.domain.aprendizado import ParametrosAprendizado, PropostaRegra
from app.domain.enums import Classe, MotivoCodificado
from app.main import app

CHAVES = {"proposta_id", "procedimento_id", "procedimento", "motivo", "classe_de", "classe_para",
          "direcao", "n_casos", "n_reguladores", "consistencia", "casos", "status", "motivo_descarte"}


def _proposta(**kw):
    base = dict(proposta_id="PROP-PROC004-ps_recorrente-C-B", procedimento_id="PROC004",
                motivo=MotivoCodificado.PS_RECORRENTE, classe_de=Classe.C, classe_para=Classe.B,
                direcao="subir", n_casos=8, n_reguladores=4, consistencia=0.89,
                casos=["DEC-SEED-001", "DEC-SEED-002"], status="pendente")
    return PropostaRegra(**{**base, **kw})


class CasoFalso:
    def __init__(self):
        self.params = ParametrosAprendizado()
        self.chamadas = 0

    def executar(self):
        self.chamadas += 1
        desc = _proposta(proposta_id="PROP-PROC018-sugestao_exagerada-B-C", procedimento_id="PROC018",
                         motivo=MotivoCodificado.SUGESTAO_EXAGERADA, classe_de=Classe.B,
                         classe_para=Classe.C, direcao="rebaixar", status="descartada",
                         motivo_descarte="I-01")
        return ResultadoGeracao(analisadas=33, consideradas=31, outros_reclassificados=1,
                                outros_sem_grupo=1, propostas=[_proposta()], descartadas=[desc])


@pytest.fixture
def caso():
    return CasoFalso()


@pytest.fixture
def client_real(monkeypatch, caso):
    monkeypatch.setattr(router, "settings", SimpleNamespace(use_mocks=False))
    app.dependency_overrides[get_gerar_propostas] = lambda: caso
    app.dependency_overrides[get_nomes_procedimentos] = lambda: {"PROC004": "Colecistectomia"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_mock_devolve_exemplo_p1_p3(monkeypatch):
    monkeypatch.setattr(router, "settings", SimpleNamespace(use_mocks=True))
    app.dependency_overrides[get_gerar_propostas] = lambda: None
    app.dependency_overrides[get_nomes_procedimentos] = lambda: {}
    try:
        r = TestClient(app).post("/aprendizado/gerar-propostas")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["propostas"][0]["proposta_id"] == "PROP-PROC004-ps_recorrente-C-B"
    assert corpo["descartadas"][0]["status"] == "descartada" and corpo["descartadas"][0]["motivo_descarte"]


def test_real_200_no_formato_do_contrato(client_real, caso):
    r = client_real.post("/aprendizado/gerar-propostas")
    assert r.status_code == 200 and caso.chamadas == 1
    corpo = r.json()
    assert set(corpo) == {"analisadas", "consideradas", "outros_reclassificados", "outros_sem_grupo",
                          "propostas", "descartadas"}
    assert corpo["analisadas"] == 33 and corpo["outros_sem_grupo"] == 1
    p = corpo["propostas"][0]
    assert set(p) == CHAVES
    assert p["procedimento"] == "Colecistectomia" and p["motivo"] == "ps_recorrente"
    assert p["classe_de"] == "C" and p["classe_para"] == "B" and p["casos"] == ["DEC-SEED-001", "DEC-SEED-002"]
    d = corpo["descartadas"][0]
    assert d["procedimento"] is None and d["direcao"] == "rebaixar" and d["motivo_descarte"] == "I-01"
    assert caso.params == ParametrosAprendizado()


def test_parametros_do_corpo_substituem_so_os_informados(client_real, caso):
    r = client_real.post("/aprendizado/gerar-propostas", json={"min_casos": 3, "min_consistencia": 0.5})
    assert r.status_code == 200
    assert caso.params == ParametrosAprendizado(min_casos=3, min_consistencia=0.5)


@pytest.mark.parametrize("corpo", [{"min_casos": 0}, {"min_reguladores": -1}, {"janela_dias": 0},
                                   {"min_consistencia": 0}, {"min_consistencia": 1.5}])
def test_parametros_invalidos_422(client_real, corpo):
    assert client_real.post("/aprendizado/gerar-propostas", json=corpo).status_code == 422
