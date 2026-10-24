"""PRE-12 · D-125: câncer escondido do laudo à fila, pela composição real (precisa do Postgres de teste).

Evento de biópsia -> PRE-12 -> LLM sugere o CID (aqui um sugestor falso, sem rede) -> regulador
corrige -> o CID novo vale para tudo (oncológico, camada 1) e o original continua guardado.
"""
import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api import deps
from app.api.deps import get_scorer as SWALIS_REAL  # antes de a fixture trocar pelo stub
from app.api.routers import eventos as roteador_eventos
from app.api.routers import inbox as roteador_inbox
from app.api.routers import pendencias as roteador_pendencias
from app.api.routers import solicitacoes as roteador_solicitacoes
from app.config import settings
from app.domain.models import SugestaoCid
from app.infrastructure.db import get_session
from app.infrastructure.swalis_stub import SwalisStub
from app.infrastructure.tables import CorrecaoTable, PendenciaTable, SolicitacaoTable
from app.main import app

from tests.infrastructure.test_resolver_pendencia import carregar

ESCONDIDO = "SOL-2026-00757"  # D37.4 (comportamento incerto do cólon) com biópsia "carcinoma papilifero"
HERNIA = "SOL-2026-00239"     # K40.9, sem biópsia no dataset


class SugestorFalso:
    modelo = "falso"

    def __init__(self):
        self.cid, self.citacao, self.laudos = "C18.9", None, []

    def sugerir(self, procedimento, cid_atual, cid_descricao, laudo):
        self.laudos.append(laudo)
        citacao = self.citacao or laudo.split(":")[-1].strip(" .")
        return SugestaoCid(cid=self.cid, descricao="(do LLM)", citacao=citacao, confianca=0.9, modelo="falso")


@pytest.fixture
def sugestor():
    return SugestorFalso()


@pytest.fixture
def api(session, tmp_path, monkeypatch, sugestor):
    """Back real (mocks desligados), banco de teste, SWALIS stub, saída em tmp_path e LLM falso."""
    carregar(session)
    sem_mocks = dataclasses.replace(settings, use_mocks=False)
    for modulo in (roteador_eventos, roteador_inbox, roteador_pendencias, roteador_solicitacoes):
        monkeypatch.setattr(modulo, "settings", sem_mocks)
    monkeypatch.setattr(deps, "settings", dataclasses.replace(settings, output_dir=tmp_path))
    monkeypatch.setattr(deps, "get_scorer", lambda data=None: SwalisStub())
    monkeypatch.setattr(deps, "criar_sugestor_cid", lambda apenas_cache=False: sugestor)
    app.dependency_overrides[get_session] = lambda: session
    # a tarefa de segundo plano abre sessão própria; no teste ela usa o banco de teste
    app.dependency_overrides[deps.get_sugerir_cid_em_segundo_plano] = (
        lambda: lambda pid: deps.montar_sugerir_cid(session).executar(pid))
    yield TestClient(app)
    app.dependency_overrides.clear()


def pre12(session, sol_id):
    return session.exec(select(PendenciaTable).where(
        PendenciaTable.solicitacao_id == sol_id, PendenciaTable.regra == "PRE-12")).one()


def test_sugestao_fica_na_pendencia(api, session):
    r = api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/sugerir-cid")

    assert r.status_code == 200
    corpo = r.json()
    assert (corpo["cid"], corpo["citacao"]) == ("C18.9", "carcinoma papilifero")
    assert corpo["descricao"].startswith("Neoplasia maligna do c")  # descrição oficial, não a do LLM
    itens = api.get("/pendencias", params={"regra": "PRE-12"}).json()["itens"]
    assert next(i for i in itens if i["solicitacao_id"] == ESCONDIDO)["sugestao_cid"]["cid"] == "C18.9"


def test_sugestao_sobrevive_a_ressincronizacao_das_pendencias(api, session):
    api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/sugerir-cid")

    carregar(session)  # recarga reescreve as evidências das pendências abertas

    assert pre12(session, ESCONDIDO).sugestao_cid_json is not None


def test_citacao_que_nao_esta_no_laudo_e_descartada(api, session, sugestor):
    sugestor.citacao = "adenocarcinoma invasivo"

    r = api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/sugerir-cid")

    assert r.status_code == 200 and r.json() is None
    assert pre12(session, ESCONDIDO).sugestao_cid_json is None


def test_corrigir_cid_vira_oncologico_e_guarda_o_original(api, session):
    p = pre12(session, ESCONDIDO)

    r = api.post(f"/pendencias/{p.pendencia_id}/resolver",
                 json={"resolucao": "corrigir_cid", "usuario_id": "reg-01", "cid": "C18.9"})

    assert r.status_code == 200 and r.json()["fila_publicada"] is True
    session.expire_all()
    t = session.get(SolicitacaoTable, ESCONDIDO)
    assert (t.cid_principal, t.cid_confirmado, t.oncologico) == ("D37.4", "C18.9", True)  # I-10 e I-09
    assert "revisar_cid" not in t.alertas_json
    log = session.exec(select(CorrecaoTable).where(CorrecaoTable.solicitacao_id == ESCONDIDO,
                                                   CorrecaoTable.regra == "PRE-12")).one()
    assert (log.campo, log.original, log.novo) == ("cid_principal", "D37.4", "C18.9")
    assert (pre12(session, ESCONDIDO).status, pre12(session, ESCONDIDO).resolucao) == ("resolvida", "corrigir_cid")
    detalhe = api.get(f"/solicitacoes/{ESCONDIDO}").json()
    assert (detalhe["cid"], detalhe["cid_original"], detalhe["camada"]) == ("C18.9", "D37.4", 1)


def test_correcao_sobrevive_a_recarga_do_dataset(api, session):
    api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/resolver",
             json={"resolucao": "corrigir_cid", "usuario_id": "reg-01", "cid": "C18.9"})

    carregar(session)  # a carga regrava as colunas do CSV, inclusive o cid_principal original

    session.expire_all()
    t = session.get(SolicitacaoTable, ESCONDIDO)
    assert (t.cid_principal, t.cid_confirmado, t.oncologico, t.cid_norm) == ("D37.4", "C18.9", True, "C189")
    assert pre12(session, ESCONDIDO).status == "resolvida"  # não reabre: o CID em vigor já é C


def test_cid_inexistente_e_recusado(api, session):
    r = api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/resolver",
                 json={"resolucao": "corrigir_cid", "usuario_id": "reg-01", "cid": "C99.9"})

    assert r.status_code == 422
    assert pre12(session, ESCONDIDO).status == "aberta"


def test_corrigir_cid_so_vale_na_pre12(api, session):
    outra = session.exec(select(PendenciaTable).where(PendenciaTable.regra == "PRE-23")).first()

    r = api.post(f"/pendencias/{outra.pendencia_id}/resolver",
                 json={"resolucao": "corrigir_cid", "usuario_id": "reg-01", "cid": "C18.9"})

    assert r.status_code == 422


def test_biopsia_positiva_nova_abre_a_pre12_e_ja_traz_a_sugestao(api, session, sugestor):
    sugestor.cid = "C16.9"

    r = api.post("/eventos", json={"solicitacao_id": HERNIA, "data_evento": "2026-10-20",
                                   "tipo_evento": "biopsia", "resultado": "positivo",
                                   "descricao": "AP: adenocarcinoma gastrico."})

    assert r.status_code == 201
    p = pre12(session, HERNIA)
    assert r.json()["pendencia_id"] == p.pendencia_id and p.status == "aberta"
    assert sugestor.laudos == ["AP: adenocarcinoma gastrico."]
    assert '"cid": "C16.9"' in p.sugestao_cid_json
    session.expire_all()
    t = session.get(SolicitacaoTable, HERNIA)
    assert t.cid_confirmado is None and t.oncologico is False  # nada muda sem o regulador (I-05)
    assert "revisar_cid" in t.alertas_json


def test_correcao_que_muda_a_classe_nao_vale_sem_o_regulador(api, session, monkeypatch):
    """I-04 (guardião): o CID novo pode mudar a classe sugerida (pele: C44.3 sai de A2 para B no SWALIS).
    Quem nunca foi confirmado fica com a classe anterior em vigor; a nova vai para o inbox."""
    monkeypatch.setattr(deps, "get_scorer", SWALIS_REAL)
    antes = api.get(f"/solicitacoes/{ESCONDIDO}").json()["score"]["classe_sistema"]

    r = api.post(f"/pendencias/{pre12(session, ESCONDIDO).pendencia_id}/resolver",
                 json={"resolucao": "corrigir_cid", "usuario_id": "reg-01", "cid": "C44.3"})

    assert r.status_code == 200
    session.expire_all()
    t = session.get(SolicitacaoTable, ESCONDIDO)
    sugerida = api.get(f"/solicitacoes/{ESCONDIDO}").json()["score"]["classe_sistema"]
    assert sugerida != antes, "pré-condição: o CID novo muda a classe sugerida"
    assert t.classe_sistema == antes and t.classe_status != "confirmada"  # congelada até o regulador
    assert ESCONDIDO in [i["solicitacao_id"] for i in api.get("/inbox").json()["itens"]]
