"""US-21 · GET /solicitacoes/{id} com caso de uso falso e mock desligado (sem banco)."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.routers.solicitacoes as solicitacoes_router
from app.api.deps import get_detalhar_solicitacao
from app.domain.enums import Classe, ClasseStatus
from app.domain.models import Motivo, Pendencia, Evento, Correcao, Procedimento
from app.main import app
from tests.application.test_detalhar_solicitacao import (
    CorrecoesFalsas, EventosFalsos, FilaFalsa, PendenciasFalsas, ProcedimentosFalsos, ScorerFalso, SolicitacoesFalsas,
    REF, linha, sol,
)
from app.application.detalhar_solicitacao import DetalharSolicitacao

CHAVES_CONTRATO = {
    "solicitacao_id", "paciente_id", "nome_paciente", "idade", "sexo", "municipio", "procedimento",
    "cid", "cid_descricao", "cid_original", "status_fila", "posicao", "camada", "camada_motivo", "score",
    "explicacao", "eventos", "decisoes", "pendencias", "alertas", "correcoes", "procedimento_info",
}


def _caso(solicitacoes):
    return DetalharSolicitacao(
        solicitacoes=SolicitacoesFalsas(*solicitacoes),
        eventos=EventosFalsos([Evento("EVT-1", "SOL-1", "PAC-1", date(2023, 1, 30), "biopsia",
                                      resultado="positivo", historico=True, origem="UPA Centro",
                                      valor_numerico=3.0)]),
        correcoes=CorrecoesFalsas([Correcao("SOL-1", "flag_oncologico", "nao", "sim", "PRE-05")]),
        pendencias=PendenciasFalsas([Pendencia(
            "PEN-0001", "SOL-1", "PRE-25", "Fontes contraditórias", True,
            [Motivo("ponto", "Pct nao deseja", "evento", ref="EVT-566")], "Ligar")]),
        fila=FilaFalsa([linha()]),
        scorer=ScorerFalso(motivos=[Motivo("eixo_progressao", "progressão 3", "regra")]),
        ref_date=REF,
        procedimentos=ProcedimentosFalsos(Procedimento("P-1", "medio", 3, 90, "nao")),
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(solicitacoes_router, "settings", SimpleNamespace(use_mocks=False))
    app.dependency_overrides[get_detalhar_solicitacao] = lambda: _caso([sol()])
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_solicitacao_200_no_formato_do_contrato(client):
    r = client.get("/solicitacoes/SOL-1")
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == CHAVES_CONTRATO
    assert corpo["solicitacao_id"] == "SOL-1"
    assert corpo["posicao"] == 1 and corpo["camada"] == 1
    assert corpo["camada_motivo"] == "Oncológico pelo CID C18.7"
    assert corpo["score"]["classe_sistema"] == "A2"
    assert corpo["score"]["classe_status"] == ClasseStatus.SUGERIDA_NAO_CONFIRMADA.value
    assert corpo["score"]["motivos"][0]["sinal"] == "eixo_progressao"
    assert corpo["eventos"][0]["historico"] is True
    assert corpo["eventos"][0]["duplicado"] is False
    assert corpo["eventos"][0]["origem"] == "UPA Centro"
    assert corpo["eventos"][0]["valor_numerico"] == 3.0
    assert corpo["procedimento_info"] == {"porte": "medio", "risco_cirurgico": 3,
                                          "duracao_media_min": 90, "necessita_uti": "nao"}
    assert corpo["decisoes"] == []
    assert corpo["pendencias"][0]["pendencia_id"] == "PEN-0001"
    assert corpo["pendencias"][0]["status"] == "aberta"
    assert corpo["correcoes"][0]["regra"] == "PRE-05"
    assert "C18.7" in corpo["explicacao"]


def test_get_solicitacao_inexistente_404(client):
    app.dependency_overrides[get_detalhar_solicitacao] = lambda: _caso([])
    r = client.get("/solicitacoes/SOL-NAO-EXISTE")
    assert r.status_code == 404
    corpo = r.json()
    assert corpo["erro"] == "SOLICITACAO_NAO_ENCONTRADA"
    assert "mensagem" in corpo


def test_mock_quando_use_mocks_ligado(monkeypatch):
    monkeypatch.setattr(solicitacoes_router, "settings", SimpleNamespace(use_mocks=True))
    r = TestClient(app).get("/solicitacoes/SOL-XYZ")
    assert r.status_code == 200
    assert r.json()["solicitacao_id"] == "SOL-XYZ"
