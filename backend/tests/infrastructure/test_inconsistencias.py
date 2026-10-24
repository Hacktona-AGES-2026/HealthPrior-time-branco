"""US-05 · alertas e pendências não bloqueantes, com o dataset real (precisa do Postgres de teste)."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select, text

from app.application.carga_inicial import CargaInicial
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlPendenciaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.tables import PendenciaTable, SolicitacaoTable
from app.main import app

DATA = settings.data_dir
ESPERADO = {"PRE-10": 39, "PRE-11": 28, "PRE-12": 23, "PRE-13": 18, "PRE-14": 50, "PRE-15": 93}


def detectar(session) -> DetectarInconsistencias:
    return DetectarInconsistencias(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                                   SqlPendenciaRepository(session), settings.ref_date)


def carregar(session):
    """A carga como o CLI faz: normalização, flags e inconsistências na mesma transação."""
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    flags = RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                            SqlCorrecaoRepository(session))
    return CargaInicial(LeitorDataset(DATA), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session), flags, detectar(session)).executar()


def reprocessar(session):
    """O comando avulso `inconsistencias`: recalcula e confirma."""
    resumo = detectar(session).executar()
    SqlUnidadeDeTrabalho(session).confirmar()
    return resumo


@pytest.fixture
def carregado(_dataset_carregado):
    """Carga feita uma vez por módulo (conftest); `session` aponta para esse banco."""
    return _dataset_carregado[1].inconsistencias


def alertas(session, sol_id):
    session.expire_all()
    return json.loads(session.get(SolicitacaoTable, sol_id).alertas_json)


def pendencias(session, sol_id=None, regra=None):
    consulta = select(PendenciaTable).order_by(PendenciaTable.pendencia_id)
    if sol_id:
        consulta = consulta.where(PendenciaTable.solicitacao_id == sol_id)
    if regra:
        consulta = consulta.where(PendenciaTable.regra == regra)
    session.expire_all()
    return session.exec(consulta).all()


def test_resumo_do_dataset(carregado):
    assert carregado.solicitacoes == 941
    assert carregado.alertas == ESPERADO
    assert (carregado.pendencias.abertas, carregado.pendencias.atualizadas,
            carregado.pendencias.encerradas) == (108, 0, 0)


@pytest.mark.parametrize("sol_id, alerta, regra", [
    ("SOL-2025-00053", "contato_perdido", "PRE-10"),              # "NUMERO NAO EXISTE"
    ("SOL-2026-00059", "contato_via_acs", "PRE-11"),              # sem telefone, via ACS
    ("SOL-2026-00757", "revisar_cid", "PRE-12"),                  # D37.4 com biópsia positiva
    ("SOL-2026-00444", "diabetes_fora_do_cadastro", "PRE-13"),    # HbA1c 9,4%, diabetes fora do cadastro
])
def test_casos_do_dataset_geram_alerta_e_pendencia_nao_bloqueante(session, carregado, sol_id, alerta, regra):
    assert alerta in alertas(session, sol_id)
    (pendencia,) = pendencias(session, sol_id, regra)
    assert (pendencia.bloqueante, pendencia.status) == (False, "aberta")
    assert pendencia.acao_sugerida


def test_justificativa_vazia_so_alerta_sem_pendencia(session, carregado):
    # SOL-2026-00932: "Solicito cirurgia."
    assert "informacao_insuficiente" in alertas(session, "SOL-2026-00932")
    assert pendencias(session, "SOL-2026-00932", "PRE-14") == []


def test_campo_vazio_so_alerta_sem_pendencia(session, carregado):
    assert not pendencias(session, regra="PRE-15")
    assert sum("cadastro_incompleto" in alertas(session, s) for s in
               session.exec(select(SolicitacaoTable.solicitacao_id)).all()) == 93


def test_ninguem_sai_da_fila(session, carregado):
    status = set(session.exec(select(SolicitacaoTable.status_fila)).all())
    assert status == {"ativa"}


def test_so_pendencias_nao_bloqueantes_das_regras_10_a_13(session, carregado):
    todas = pendencias(session)
    assert len(todas) == 108
    assert {p.regra for p in todas} == {"PRE-10", "PRE-11", "PRE-12", "PRE-13"}
    assert not any(p.bloqueante for p in todas)


def test_ids_das_pendencias_sao_unicos_e_sequenciais(session, carregado):
    ids = [p.pendencia_id for p in pendencias(session)]

    assert ids == [f"PEN-{n:04d}" for n in range(1, 109)]


def test_evidencia_cita_o_trecho_de_origem(session, carregado):
    (p,) = pendencias(session, "SOL-2026-00757", "PRE-12")

    evidencias = json.loads(p.evidencias_json)
    assert {e["fonte"] for e in evidencias} == {"evento", "cid"}
    biopsia = next(e for e in evidencias if e["fonte"] == "evento")
    assert biopsia["ref"].startswith("EVT-") and biopsia["texto"]


def test_dados_originais_continuam_intactos(session, carregado):
    s = session.get(SolicitacaoTable, "SOL-2025-00053")

    assert s.observacoes == "NAO ATENDE. NUMERO NAO EXISTE."


def test_reprocessar_e_idempotente(session, carregado):
    ids = [p.pendencia_id for p in pendencias(session)]

    resumo = reprocessar(session)

    assert (resumo.pendencias.abertas, resumo.pendencias.atualizadas, resumo.pendencias.encerradas) == (0, 0, 0)
    assert [p.pendencia_id for p in pendencias(session)] == ids
    assert resumo.alertas == ESPERADO


def test_recarga_do_dataset_nao_duplica(session):
    carregar(session)
    resumo = carregar(session).inconsistencias

    assert resumo.pendencias.abertas == 0
    assert len(pendencias(session)) == 108


def test_pendencia_resolvida_por_pessoa_nao_e_reaberta(session, carregado):
    (p,) = pendencias(session, "SOL-2025-00053", "PRE-10")
    session.exec(text("update pendencias set status='resolvida', resolvido_por='adm-01', "
                      "resolucao='contato atualizado' where pendencia_id = :i").bindparams(i=p.pendencia_id))
    session.commit()

    resumo = reprocessar(session)

    (depois,) = pendencias(session, "SOL-2025-00053", "PRE-10")
    assert (depois.status, depois.resolvido_por, depois.resolucao) == ("resolvida", "adm-01", "contato atualizado")
    assert resumo.pendencias.abertas == 0 and len(pendencias(session)) == 108


def test_pendencia_descartada_nao_e_reaberta(session, carregado):
    session.exec(text("update pendencias set status='descartada' where solicitacao_id='SOL-2026-00444'"))
    session.commit()

    reprocessar(session)

    (p,) = pendencias(session, "SOL-2026-00444", "PRE-13")
    assert p.status == "descartada"


def test_pendencia_encerra_sozinha_quando_o_achado_deixa_de_valer(session, carregado):
    session.exec(text("update solicitacoes set observacoes = null where solicitacao_id='SOL-2026-00059'"))
    session.commit()

    resumo = reprocessar(session)

    (p,) = pendencias(session, "SOL-2026-00059", "PRE-11")
    assert (p.status, p.resolvido_por, p.resolucao) == ("resolvida", "sistema", "deixou_de_valer")
    assert p.resolvido_em is not None
    assert resumo.pendencias.encerradas == 1
    assert "contato_via_acs" not in alertas(session, "SOL-2026-00059")


def test_achado_novo_abre_pendencia_com_o_proximo_id(session, carregado):
    session.exec(text("update solicitacoes set observacoes = 'NAO ATENDE. NUMERO NAO EXISTE.' "
                      "where solicitacao_id='SOL-2025-00048'"))
    session.commit()

    resumo = reprocessar(session)

    (p,) = pendencias(session, "SOL-2025-00048", "PRE-10")
    assert p.pendencia_id == "PEN-0109"
    assert resumo.pendencias.abertas == 1


def test_evidencia_atualizada_nas_pendencias_abertas(session, carregado):
    session.exec(text("update solicitacoes set observacoes = 'NAO ATENDE. NUMERO NAO EXISTE. Carta devolvida.' "
                      "where solicitacao_id='SOL-2025-00053'"))
    session.commit()

    resumo = reprocessar(session)

    (p,) = pendencias(session, "SOL-2025-00053", "PRE-10")
    assert "Carta devolvida" in p.evidencias_json
    assert resumo.pendencias.atualizadas == 1


def test_alertas_de_outras_regras_sao_preservados(session, carregado):
    session.exec(text("update solicitacoes set alertas_json = '[\"alerta_de_outra_regra\"]' "
                      "where solicitacao_id='SOL-2025-00053'"))
    session.commit()

    reprocessar(session)

    resultado = alertas(session, "SOL-2025-00053")
    assert resultado[0] == "alerta_de_outra_regra"          # fica, no início
    assert "contato_perdido" in resultado                    # os desta US são recolocados
    assert len(resultado) == len(set(resultado))             # sem repetir


def test_aberta_em_usa_a_data_de_referencia(session, carregado):
    datas = {p.aberta_em for p in pendencias(session)}

    assert datas == {settings.ref_date}


def test_post_admin_carga_traz_as_inconsistencias(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        resp = TestClient(app).post("/admin/carga")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["inconsistencias"] == {
        "solicitacoes": 941, "alertas": ESPERADO,
        "pendencias": {"abertas": 108, "atualizadas": 0, "encerradas": 0},
    }
