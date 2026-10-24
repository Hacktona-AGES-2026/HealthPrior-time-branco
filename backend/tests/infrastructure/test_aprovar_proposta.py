"""US-13 · POST /decisoes (aprovar) com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select, text

from app.api import deps
from app.api.routers import decisoes as roteador
from app.application.gerar_fila import GerarFila
from app.application.publicar_fila import PublicarFila
from app.config import settings
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlDecisaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.tables import DecisaoTable, SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial
from app.main import app
from tests.infrastructure.test_resolver_pendencia import carregar

ALVO = "SOL-2025-00048"  # no inbox do dataset: sugerida A2, prioridade manual "baixa" (implícita D)
AGORA = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


class VerificadorReprova:
    def verificar(self, caminho):
        return False, "reprovado"


def publicar(session, tmp_path, verificador=None):
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), criar_swalis(),
                      ExportadorCsv(), settings.ref_date)
    return PublicarFila(gerar, verificador or VerificadorOficial(), SqlFilaRepository(session),
                        SqlUnidadeDeTrabalho(session), lambda: AGORA, tmp_path).executar()


@pytest.fixture
def api(session, tmp_path, monkeypatch):
    """Back real (mocks desligados) com o banco de teste e uma fila já publicada."""
    carregar(session)
    publicar(session, tmp_path)
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=False))
    monkeypatch.setattr(deps, "settings", dataclasses.replace(settings, output_dir=tmp_path))
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def aprovar(api, sol_id=ALVO, regulador="reg-01", **extra):
    return api.post("/decisoes", json={"solicitacao_id": sol_id, "regulador_id": regulador, "acao": "aprovar", **extra})


def inbox_ids(session):
    from app.application.listar_inbox import ListarInbox
    caso = ListarInbox(SqlFilaRepository(session), SqlSolicitacaoRepository(session),
                       SqlEventoRepository(session), criar_swalis())
    return [i.solicitacao_id for i in caso.executar().itens]


def posicao(session, sol_id):
    return next((l.posicao for l in SqlFilaRepository(session).obter_publicada() if l.solicitacao_id == sol_id), None)


def solicitacao(session, sol_id):
    session.expire_all()
    return session.get(SolicitacaoTable, sol_id)


def test_o_alvo_esta_no_inbox_antes(api, session):
    assert ALVO in inbox_ids(session)


def test_aprovar_confirma_a_classe_e_responde_o_contrato(api, session):
    antes = posicao(session, ALVO)

    r = aprovar(api)

    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"decisao_id", "posicao_anterior", "posicao_nova", "fila_publicada"}
    assert corpo["decisao_id"] == "DEC-0001" and corpo["fila_publicada"] is True
    assert corpo["posicao_anterior"] == antes
    assert corpo["posicao_nova"] == posicao(session, ALVO)  # a posição vem da fila republicada
    s = solicitacao(session, ALVO)
    assert (s.classe_status, s.classe_confirmada) == ("confirmada", "A2")


def test_aprovar_tira_o_paciente_do_inbox_e_so_ele(api, session):
    antes = inbox_ids(session)

    aprovar(api)

    depois = inbox_ids(session)
    assert ALVO not in depois and sorted(depois) == sorted(i for i in antes if i != ALVO)


def test_aprovar_registra_a_decisao_no_log(api, session):
    aprovar(api, regulador="reg-03")

    (d,) = SqlDecisaoRepository(session).listar_por_solicitacao(ALVO)
    assert (d.decisao_id, d.regulador_id, d.acao.value) == ("DEC-0001", "reg-03", "aprovar")
    assert d.classe_sugerida.value == d.classe_decidida.value == "A2"
    assert d.versao_regras and d.procedimento_id and d.justificativa is None and d.data is not None
    assert d.motivo_codificado is None and d.score_decidido is None


def test_aprovar_nao_apaga_nem_altera_dados_originais(api, session):
    antes = solicitacao(session, ALVO)
    original = (antes.prioridade_regulacao, antes.justificativa_clinica, antes.observacoes, str(antes.data_entrada_fila))

    aprovar(api)

    s = solicitacao(session, ALVO)
    assert (s.prioridade_regulacao, s.justificativa_clinica, s.observacoes, str(s.data_entrada_fila)) == original
    assert session.exec(select(func.count()).select_from(SolicitacaoTable)).one() == 941


def test_so_a_aprovada_fica_confirmada(api, session):
    aprovar(api)

    n = session.exec(select(func.count()).select_from(SolicitacaoTable)
                     .where(SolicitacaoTable.classe_status == "confirmada")).one()
    assert n == 1


def test_a_fila_e_republicada(api, session):
    antes = SqlFilaRepository(session).publicada_em()

    aprovar(api)

    session.expire_all()
    assert SqlFilaRepository(session).publicada_em() != antes or antes is None
    assert len(SqlFilaRepository(session).obter_publicada()) == 900


# --- 409, 404, 422 ---

def test_aprovar_duas_vezes_da_409_e_nao_duplica_o_log(api, session):
    aprovar(api)

    r = aprovar(api)

    assert r.status_code == 409 and r.json()["erro"] == "SEM_PROPOSTA"
    assert session.exec(select(func.count()).select_from(DecisaoTable)).one() == 1


def test_solicitacao_inexistente_da_404(api):
    r = aprovar(api, sol_id="SOL-9999-99999")

    assert r.status_code == 404 and r.json()["erro"] == "SOLICITACAO_NAO_ENCONTRADA"


def test_solicitacao_suspensa_nao_tem_proposta(api, session):
    r = aprovar(api, sol_id="SOL-2024-00076")  # desistência: suspensa (PRE-23)

    assert r.status_code == 409 and r.json()["erro"] == "SEM_PROPOSTA"


def test_solicitacao_fora_do_inbox_nao_tem_proposta(api, session):
    fora = next(i for i in (l.solicitacao_id for l in SqlFilaRepository(session).obter_publicada())
                if i not in set(inbox_ids(session)))

    r = aprovar(api, sol_id=fora)

    assert r.status_code == 409 and r.json()["erro"] == "SEM_PROPOSTA"


@pytest.mark.parametrize("acao", ["editar", "manter"])
def test_editar_e_manter_sem_justificativa_dao_422(api, session, acao):
    r = api.post("/decisoes", json={"solicitacao_id": ALVO, "regulador_id": "reg-01", "acao": acao, "classe": "B"})

    assert r.status_code == 422 and r.json()["erro"] == "JUSTIFICATIVA_OBRIGATORIA"
    assert session.exec(select(func.count()).select_from(DecisaoTable)).one() == 0


def test_editar_vale_fora_do_inbox(api, session):
    fora = next(i for i in (l.solicitacao_id for l in SqlFilaRepository(session).obter_publicada())
                if i not in set(inbox_ids(session)))

    r = api.post("/decisoes", json={"solicitacao_id": fora, "regulador_id": "reg-01", "acao": "editar",
                                    "classe": "B", "motivo_codificado": "outro", "justificativa": "teste"})

    assert r.status_code == 200 and r.json()["decisao_id"] == "DEC-0001"  # só aprovar exige proposta (D-94)


def test_regulador_e_obrigatorio(api):
    r = api.post("/decisoes", json={"solicitacao_id": ALVO, "acao": "aprovar"})

    assert r.status_code == 422


# --- override anterior (US-14) ---

def test_aprovar_remove_o_override_e_o_paciente_sobe(api, session):
    session.exec(text("update solicitacoes set classe_medico='D', score_medico=1, editado_manualmente=true, "
                      "editado_por='reg-02', editado_em='2026-10-12 09:00' where solicitacao_id=:i").bindparams(i=ALVO))
    session.commit()
    from app.api.routers.pendencias import settings as _  # noqa: F401  (garante o módulo carregado)
    publicar(session, api.app.dependency_overrides and deps.settings.output_dir)  # fila com o override valendo
    antes = posicao(session, ALVO)

    r = aprovar(api)

    assert r.status_code == 200
    s = solicitacao(session, ALVO)
    assert (s.classe_medico, s.score_medico, s.editado_manualmente, s.editado_por) == (None, None, False, None)
    (d,) = SqlDecisaoRepository(session).listar_por_solicitacao(ALVO)
    assert d.justificativa == "Override anterior removido (classe D, score 1; editado por reg-02 em 12/10/2026)."
    assert r.json()["posicao_anterior"] == antes
    assert r.json()["posicao_nova"] < antes  # sem o override D, vale a classe A2 do SWALIS


# --- a decisão vale mesmo se a fila não for republicada (I-07, D-96) ---

def test_verificador_reprova_a_decisao_fica_e_a_posicao_nao_muda(api, session, monkeypatch):
    anterior = SqlFilaRepository(session).obter_publicada()
    monkeypatch.setattr(deps, "VerificadorOficial", VerificadorReprova)

    r = aprovar(api)

    assert r.status_code == 200 and r.json()["fila_publicada"] is False
    assert r.json()["posicao_nova"] == r.json()["posicao_anterior"]
    assert solicitacao(session, ALVO).classe_status == "confirmada"  # a decisão ficou
    assert SqlFilaRepository(session).obter_publicada() == anterior  # a fila anterior segue valendo


def test_falha_ao_publicar_nao_desfaz_a_decisao(api, session, monkeypatch):
    def quebra(self):
        raise OSError("disco cheio")

    monkeypatch.setattr(PublicarFila, "executar", quebra)

    r = aprovar(api)

    assert r.status_code == 200 and r.json()["fila_publicada"] is False
    assert solicitacao(session, ALVO).classe_status == "confirmada"
    assert session.exec(select(func.count()).select_from(DecisaoTable)).one() == 1


def test_com_mocks_ligados_devolve_o_contrato_fixo(session, monkeypatch):
    monkeypatch.setattr(roteador, "settings", dataclasses.replace(settings, use_mocks=True))
    app.dependency_overrides[get_session] = lambda: session
    try:
        r = TestClient(app).post("/decisoes", json={"solicitacao_id": ALVO, "regulador_id": "reg-01", "acao": "aprovar"})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200 and r.json()["decisao_id"] == "DEC-MOCK"
