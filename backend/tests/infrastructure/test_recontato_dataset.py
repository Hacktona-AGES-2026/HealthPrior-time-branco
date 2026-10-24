"""US-17 · recontato com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select

from app import cli
from app.api import deps
from app.api.routers import pendencias as roteador_pendencias
from app.application.atualizacao_diaria import AtualizacaoDiaria
from app.application.detectar_recontato import DetectarRecontato
from app.application.gerar_fila import GerarFila
from app.application.publicar_fila import PublicarFila
from app.config import settings
from app.domain.models import Evento
from app.domain.recontato import REC_SEM_EVENTO
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlEventoRepository,
    SqlFilaRepository,
    SqlPendenciaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import SwalisRegras
from app.infrastructure.tables import PendenciaTable, SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial
from app.main import app
from tests.infrastructure.test_resolver_pendencia import carregar

HOJE = settings.ref_date


def recontato(session, n=180, hoje=HOJE):
    r = DetectarRecontato(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                          SqlPendenciaRepository(session), hoje, n).executar()
    session.commit()
    return r


def abertas(session):
    session.expire_all()
    return session.exec(select(PendenciaTable).where(
        PendenciaTable.regra == REC_SEM_EVENTO, PendenciaTable.status == "aberta")).all()


def test_abre_uma_pendencia_nao_bloqueante_por_ativa_sem_evento_recente(session):
    carregar(session)
    r = recontato(session)
    assert r.n_dias == 180 and r.sem_evento > 0 and r.pendencias.abertas == r.sem_evento
    pend = abertas(session)
    assert len(pend) == r.sem_evento and all(not p.bloqueante for p in pend)
    suspensas = {s.solicitacao_id for s in SqlSolicitacaoRepository(session).listar(apenas_ativas=False)
                 if s.status_fila.value != "ativa"}
    assert not suspensas & {p.solicitacao_id for p in pend}  # só quem está esperando na fila


def test_n_configuravel_e_idempotente(session):
    carregar(session)
    grande = recontato(session, n=180).sem_evento
    de_novo = recontato(session, n=180)
    assert (de_novo.pendencias.abertas, de_novo.pendencias.encerradas) == (0, 0)
    menor = recontato(session, n=90)
    assert menor.sem_evento > grande and menor.pendencias.abertas == menor.sem_evento - grande
    maior = recontato(session, n=365)
    assert maior.sem_evento < grande and maior.pendencias.encerradas == menor.sem_evento - maior.sem_evento
    assert len(abertas(session)) == maior.sem_evento


def test_o_retorno_do_contato_vira_evento_e_encerra_a_pendencia(session):
    carregar(session)
    recontato(session)
    alvo = abertas(session)[0].solicitacao_id
    s = SqlSolicitacaoRepository(session).obter(alvo)
    SqlEventoRepository(session).adicionar(Evento("EVT-REC-1", alvo, s.paciente_id, HOJE, "contato_telefonico", "atendeu"))
    session.commit()
    r = recontato(session)
    assert r.pendencias.encerradas == 1 and alvo not in {p.solicitacao_id for p in abertas(session)}


def test_nao_altera_classe_nem_status_nem_posicao(session, tmp_path):
    carregar(session)

    def publicar():
        gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), SwalisRegras(),
                          ExportadorCsv(), HOJE)
        PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
                     lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()
        return [(l.solicitacao_id, l.posicao, l.classe) for l in SqlFilaRepository(session).obter_publicada()]

    antes = publicar()
    estado = session.exec(select(SolicitacaoTable.solicitacao_id, SolicitacaoTable.status_fila,
                                 SolicitacaoTable.classe_status)).all()
    recontato(session)
    assert publicar() == antes
    assert session.exec(select(SolicitacaoTable.solicitacao_id, SolicitacaoTable.status_fila,
                               SolicitacaoTable.classe_status)).all() == estado


def test_atualizacao_diaria_roda_o_recontato_com_a_data_simulada(session, tmp_path, monkeypatch):
    carregar(session)
    monkeypatch.setattr(deps, "settings", dataclasses.replace(settings, output_dir=tmp_path, recontato_dias=180))
    monkeypatch.setattr(deps, "get_scorer", lambda data=None: SwalisRegras(ref_date=data))
    app.dependency_overrides[get_session] = lambda: session
    try:
        c = TestClient(app)
        r1 = c.post("/admin/atualizacao-diaria", params={"data": HOJE.isoformat()})
        assert r1.status_code == 200, r1.text
        rec = r1.json()["recontato"]
        assert rec["n_dias"] == 180 and rec["sem_evento"] > 0 and rec["abertas"] == rec["sem_evento"]
        # 60 dias depois mais gente passou do limite; o resto não muda
        r2 = c.post("/admin/atualizacao-diaria", params={"data": date.fromordinal(HOJE.toordinal() + 60).isoformat()})
        assert r2.json()["recontato"]["sem_evento"] > rec["sem_evento"]
        assert r2.json()["recontato"]["abertas"] == r2.json()["recontato"]["sem_evento"] - rec["sem_evento"]
    finally:
        app.dependency_overrides.clear()


def test_aparece_na_lista_de_pendencias_e_aceita_so_reativar_ou_descartar(session, monkeypatch):
    carregar(session)
    recontato(session)
    monkeypatch.setattr(roteador_pendencias, "settings", dataclasses.replace(settings, use_mocks=False))
    app.dependency_overrides[get_session] = lambda: session
    try:
        c = TestClient(app)
        itens = c.get("/pendencias", params={"regra": REC_SEM_EVENTO}).json()["itens"]
        assert itens and itens[0]["bloqueante"] is False and "Sem evento há" in itens[0]["titulo"]
        pid = itens[0]["pendencia_id"]
        assert c.post(f"/pendencias/{pid}/resolver", json={"resolucao": "confirmar_saida", "usuario_id": "adm-01",
                                                          "observacao": "x"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_cli_imprime_o_resumo(session, monkeypatch, capsys):
    carregar(session)
    monkeypatch.setattr(cli, "engine", session.get_bind())
    cli.cmd_recontato()
    saida = capsys.readouterr().out
    assert "sem evento há 180+ dias" in saida and "abertas" in saida
