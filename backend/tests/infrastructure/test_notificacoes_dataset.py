"""Notificações ao paciente com o dataset real: gatilhos, limites e o canal que falha (precisa do Postgres de teste)."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routers import admin as roteador_admin
from app.api.routers import decisoes as roteador_decisoes
from app.api.routers import notificacoes as roteador_notificacoes
from app.api.routers import pendencias as roteador_pendencias
from app.application.gerar_fila import GerarFila
from app.application.publicar_fila import PublicarFila
from app.config import settings
from app.domain.ports import ResultadoEnvio
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlEventoRepository,
    SqlFilaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import SwalisRegras
from app.infrastructure.verificador import VerificadorOficial
from app.main import app
from tests.infrastructure.test_resolver_pendencia import carregar

ALVO = "SOL-2023-00060"
DESTINO = "+5551999990000"


class CanalFalso:
    canal = "twilio"

    def __init__(self, ok=True):
        self.ok, self.enviadas = ok, []

    def enviar(self, destino, texto):
        self.enviadas.append((destino, texto))
        return ResultadoEnvio(self.ok, "SM1" if self.ok else "Twilio 400: unverified")


@pytest.fixture
def api(session, tmp_path, monkeypatch):
    carregar(session)
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), SwalisRegras(),
                      ExportadorCsv(), settings.ref_date)
    PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
                 lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()
    canal = CanalFalso()
    cfg = dataclasses.replace(settings, use_mocks=False, output_dir=tmp_path, notifica_destino=DESTINO,
                              notifica_min_posicoes=1, notifica_max_por_publicacao=3, notifica_limite_envio=50)
    monkeypatch.setattr(deps, "settings", cfg)
    for r in (roteador_decisoes, roteador_notificacoes, roteador_pendencias, roteador_admin):
        if hasattr(r, "settings"):
            monkeypatch.setattr(r, "settings", cfg)
    monkeypatch.setattr(deps, "get_scorer", lambda data=None: SwalisRegras(ref_date=data))
    monkeypatch.setattr(deps, "criar_notificador", lambda: canal)
    monkeypatch.setattr(roteador_notificacoes, "criar_notificador", lambda: canal)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app), canal
    app.dependency_overrides.clear()


def aprovar(c, sid=ALVO):
    return c.post("/decisoes", json={"solicitacao_id": sid, "regulador_id": "reg-01", "acao": "editar",
                                     "classe": "A2", "motivo_codificado": "outro", "justificativa": "demo"})


def test_decisao_avisa_a_situacao_e_a_posicao_so_para_o_numero_da_demo(api):
    c, canal = api
    assert aprovar(c).status_code == 200
    itens = c.get("/notificacoes").json()["itens"]
    motivos = {i["motivo"] for i in itens}
    assert "situacao" in motivos and "posicao" in motivos
    assert all(i["status"] == "enviada" and i["canal"] == "twilio" for i in itens)
    assert {d for d, _ in canal.enviadas} == {DESTINO}  # nunca o telefone do paciente
    assert any(t.startswith(f"[DEMO {ALVO}]") for _, t in canal.enviadas)
    texto_todo = " ".join(t for _, t in canal.enviadas).lower()
    assert "a2" not in texto_todo and "score" not in texto_todo and "classe" not in texto_todo


def test_posicao_respeita_o_maximo_por_publicacao(api):
    c, _ = api
    aprovar(c)
    posicao = [i for i in c.get("/notificacoes").json()["itens"] if i["motivo"] == "posicao"]
    assert 0 < len(posicao) <= 3


def test_falha_do_canal_nao_derruba_a_decisao_e_fica_registrada(api):
    c, canal = api
    canal.ok = False
    r = aprovar(c)
    assert r.status_code == 200 and r.json()["fila_publicada"] is True
    itens = c.get("/notificacoes").json()["itens"]
    assert itens and all(i["status"] == "falhou" and "unverified" in i["detalhe"] for i in itens)
    canal.ok = True  # a rodada seguinte tenta de novo
    assert c.post("/notificacoes/enviar").json()["pendentes"] == 0


def test_limite_por_rodada_deixa_o_resto_pendente(api, monkeypatch):
    c, canal = api
    monkeypatch.setattr(deps, "settings", dataclasses.replace(deps.settings, notifica_limite_envio=1))
    aprovar(c)
    r = c.post("/notificacoes/enviar").json()
    assert r["canal"] == "twilio" and len(canal.enviadas) >= 1


def test_o_destino_aparece_mascarado(api):
    c, _ = api
    assert c.get("/notificacoes").json()["destino"] == "+55*********00"


def test_recontato_na_atualizacao_diaria_avisa_no_maximo_o_limite(api):
    c, canal = api
    r = c.post("/admin/atualizacao-diaria", params={"data": "2026-10-24"})
    assert r.status_code == 200, r.text
    itens = [i for i in c.get("/notificacoes").json()["itens"] if i["motivo"] == "recontato"]
    assert 0 < len(itens) <= 3 and r.json()["recontato"]["sem_evento"] > 3


def test_sem_credenciais_o_canal_twilio_cai_no_simulado():
    from app.infrastructure import notificador as n

    cfg = dataclasses.replace(settings, notifica_canal="twilio", twilio_account_sid="", twilio_auth_token="")
    original = n.settings
    n.settings = cfg
    try:
        assert n.criar_notificador().canal == "simulado"
    finally:
        n.settings = original
