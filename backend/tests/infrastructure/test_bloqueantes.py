"""US-04 · inconsistências bloqueantes e suspensão, com o dataset real (precisa do Postgres de teste)."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select, text

from app.application.carga_inicial import CargaInicial
from app.application.detectar_bloqueantes import DetectarBloqueantes
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
from app.infrastructure.tables import EventoTable, PendenciaTable, ProcedimentoTable, SolicitacaoTable
from app.main import app

DATA = settings.data_dir
ACHADOS = {"PRE-20": 22, "PRE-21": 1, "PRE-22": 2, "PRE-23": 10, "PRE-24": 9, "PRE-25": 12}


def bloqueantes(session) -> DetectarBloqueantes:
    return DetectarBloqueantes(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                               SqlPendenciaRepository(session), settings.ref_date)


def carregar(session):
    """A carga como o CLI faz: normalização, flags, inconsistências e bloqueantes, mesma transação."""
    sol, ev, cor = (SqlSolicitacaoRepository(session), SqlEventoRepository(session), SqlCorrecaoRepository(session))
    return CargaInicial(
        LeitorDataset(DATA), SqlCargaRepository(session), Normalizar(sol, cor), SqlUnidadeDeTrabalho(session),
        RecalcularFlags(sol, ev, cor),
        DetectarInconsistencias(sol, ev, SqlPendenciaRepository(session), settings.ref_date),
        bloqueantes(session)).executar()


def reprocessar(session):
    """O comando avulso `bloqueantes`: recalcula e confirma."""
    resumo = bloqueantes(session).executar()
    SqlUnidadeDeTrabalho(session).confirmar()
    return resumo


@pytest.fixture
def carregado(_dataset_carregado):
    """Carga feita uma vez por módulo (conftest); `session` aponta para esse banco."""
    return _dataset_carregado[1].bloqueantes


def solicitacao(session, sol_id):
    session.expire_all()
    return session.get(SolicitacaoTable, sol_id)


def pendencias(session, sol_id=None, regra=None):
    consulta = select(PendenciaTable).where(PendenciaTable.bloqueante).order_by(PendenciaTable.pendencia_id)
    if sol_id:
        consulta = consulta.where(PendenciaTable.solicitacao_id == sol_id)
    if regra:
        consulta = consulta.where(PendenciaTable.regra == regra)
    session.expire_all()
    return session.exec(consulta).all()


def sql(session, comando, **params):
    session.exec(text(comando).bindparams(**params))
    session.commit()


def test_resumo_do_dataset(carregado):
    assert carregado.achados == ACHADOS
    assert carregado.suspensas == 41
    assert carregado.oncologicas_a_confirmar == 5
    assert carregado.eventos_orfaos == 9
    assert (carregado.pendencias.abertas, carregado.pendencias.atualizadas, carregado.pendencias.encerradas) == (56, 0, 0)


def test_duplicata_suspende_so_a_mais_recente(session, carregado):
    # PAC-00151
    antiga, nova = solicitacao(session, "SOL-2025-00290"), solicitacao(session, "SOL-2025-00348")

    assert (antiga.status_fila, antiga.motivo_status) == ("ativa", None)
    assert (nova.status_fila, nova.motivo_status) == ("suspensa", "PRE-20")
    (p,) = pendencias(session, "SOL-2025-00348", "PRE-20")
    assert p.bloqueante and p.status == "aberta"
    assert [e["ref"] for e in json.loads(p.evidencias_json)] == ["SOL-2025-00290", "SOL-2025-00348"]
    assert "SOL-2025-00290" in p.acao_sugerida


def test_a_data_de_entrada_mais_antiga_e_mantida(session, carregado):
    assert str(solicitacao(session, "SOL-2025-00290").data_entrada_fila) == "2025-09-19"


def test_desistencia_suspende(session, carregado):
    s = solicitacao(session, "SOL-2024-00076")

    assert (s.status_fila, s.motivo_status) == ("suspensa", "PRE-23")


@pytest.mark.parametrize("sol_id", ["SOL-2026-00305", "SOL-2025-00453", "SOL-2023-00054"])
def test_fontes_que_divergem_suspendem_com_pre_25_e_as_duas_evidencias(session, carregado, sol_id):
    s = solicitacao(session, sol_id)
    (p,) = pendencias(session, sol_id, "PRE-25")

    assert (s.status_fila, s.motivo_status) == ("suspensa", "PRE-25")
    assert sorted(e["fonte"] for e in json.loads(p.evidencias_json)) == ["evento", "observacoes"]


def test_evento_orfao_nao_e_aplicado_e_gera_pendencia(session, carregado):
    # EVT-000287 -> SOL-2023-00941
    session.expire_all()
    assert session.get(EventoTable, "EVT-000287").orfao is True
    assert session.exec(select(func.count()).select_from(EventoTable).where(EventoTable.orfao)).one() == 9
    (p,) = pendencias(session, "SOL-2023-00941", "PRE-24")
    assert p.bloqueante and json.loads(p.evidencias_json)[0]["ref"] == "EVT-000287"
    assert session.get(SolicitacaoTable, "SOL-2023-00941") is None


def test_oncologico_nunca_e_suspenso_automaticamente(session, carregado):
    # PAC-00307 (C73): a duplicata fica ativa, com pendência bloqueante e alerta (I-02)
    s = solicitacao(session, "SOL-2026-01014")

    assert (s.status_fila, s.motivo_status) == ("ativa", None)
    assert "saida_a_confirmar" in json.loads(s.alertas_json)
    (p,) = pendencias(session, "SOL-2026-01014", "PRE-20")
    assert p.bloqueante and p.status == "aberta"
    suspensos = session.exec(select(func.count()).select_from(SolicitacaoTable)
                             .where(SolicitacaoTable.oncologico, SolicitacaoTable.status_fila == "suspensa")).one()
    assert suspensos == 0


def test_so_suspensas_saem_da_fila(session, carregado):
    ativas = SqlSolicitacaoRepository(session).listar(apenas_ativas=True)

    assert len(ativas) == 941 - 41
    assert "SOL-2025-00348" not in {s.solicitacao_id for s in ativas}


def test_nada_e_apagado(session, carregado):
    assert session.exec(select(func.count()).select_from(SolicitacaoTable)).one() == 941
    assert session.exec(select(func.count()).select_from(EventoTable)).one() == 1505
    assert session.exec(select(func.count()).select_from(ProcedimentoTable)).one() == 23
    assert solicitacao(session, "SOL-2024-00076").observacoes == "PCT DESISTIU DO PROCEDIMENTO. SOLICITA RETIRADA DA FILA."


def test_toda_suspensao_tem_motivo_de_uma_regra(session, carregado):
    motivos = session.exec(select(SolicitacaoTable.motivo_status)
                           .where(SolicitacaoTable.status_fila == "suspensa")).all()

    assert len(motivos) == 41 and set(motivos) <= {"PRE-20", "PRE-21", "PRE-22", "PRE-23", "PRE-25"}


def test_alertas_de_outras_regras_sao_preservados(session, carregado):
    # SOL-2025-00053 tem alertas da US-05 (contato_perdido...)
    antes = json.loads(solicitacao(session, "SOL-2025-00053").alertas_json)

    reprocessar(session)

    assert json.loads(solicitacao(session, "SOL-2025-00053").alertas_json) == antes and "contato_perdido" in antes


def test_reprocessar_e_idempotente(session, carregado):
    ids = [p.pendencia_id for p in pendencias(session)]

    resumo = reprocessar(session)

    assert resumo.achados == ACHADOS and resumo.suspensas == 41 and resumo.reativadas == 0
    assert (resumo.pendencias.abertas, resumo.pendencias.atualizadas, resumo.pendencias.encerradas) == (0, 0, 0)
    assert [p.pendencia_id for p in pendencias(session)] == ids


def test_recarga_do_dataset_nao_duplica_nem_reativa(session):
    carregar(session)
    resumo = carregar(session).bloqueantes

    assert resumo.suspensas == 41 and resumo.pendencias.abertas == 0
    assert len(pendencias(session)) == 56


def test_reativada_por_pessoa_nao_e_suspensa_de_novo(session, carregado):
    # como a US-07 fará em "reativar": pendência resolvida e solicitação de volta à fila
    sql(session, "update pendencias set status='resolvida', resolvido_por='adm-01', resolucao='reativar' "
                 "where solicitacao_id='SOL-2024-00076' and regra='PRE-23'")
    sql(session, "update solicitacoes set status_fila='ativa', motivo_status=null where solicitacao_id='SOL-2024-00076'")

    resumo = reprocessar(session)

    assert solicitacao(session, "SOL-2024-00076").status_fila == "ativa"
    (p,) = pendencias(session, "SOL-2024-00076", "PRE-23")
    assert (p.status, p.resolvido_por) == ("resolvida", "adm-01")
    assert resumo.suspensas == 40 and resumo.pendencias.abertas == 0


def test_pendencia_descartada_desfaz_a_suspensao(session, carregado):
    sql(session, "update pendencias set status='descartada', resolvido_por='adm-01' "
                 "where solicitacao_id='SOL-2025-00348' and regra='PRE-20'")

    resumo = reprocessar(session)

    s = solicitacao(session, "SOL-2025-00348")
    assert (s.status_fila, s.motivo_status) == ("ativa", None)
    assert resumo.reativadas == 1


def test_achado_que_some_encerra_a_pendencia_e_reativa(session, carregado):
    sql(session, "update solicitacoes set observacoes=null where solicitacao_id='SOL-2024-00076'")
    sql(session, "update eventos set resultado='atendeu' where solicitacao_id='SOL-2024-00076' and resultado='desistiu'")

    resumo = reprocessar(session)

    s = solicitacao(session, "SOL-2024-00076")
    assert (s.status_fila, s.motivo_status) == ("ativa", None)
    (p,) = pendencias(session, "SOL-2024-00076", "PRE-23")
    assert (p.status, p.resolvido_por, p.resolucao) == ("resolvida", "sistema", "deixou_de_valer")
    assert resumo.reativadas == 1 and resumo.pendencias.encerradas == 1


def test_removida_nunca_e_alterada(session, carregado):
    sql(session, "update solicitacoes set status_fila='removida', motivo_status='confirmar_saida' "
                 "where solicitacao_id='SOL-2024-00076'")

    reprocessar(session)

    s = solicitacao(session, "SOL-2024-00076")
    assert (s.status_fila, s.motivo_status) == ("removida", "confirmar_saida")


def test_oncologico_suspenso_antes_volta_para_a_fila(session, carregado):
    sql(session, "update solicitacoes set status_fila='suspensa', motivo_status='PRE-20' where solicitacao_id='SOL-2026-01014'")

    resumo = reprocessar(session)

    assert solicitacao(session, "SOL-2026-01014").status_fila == "ativa"
    assert resumo.reativadas == 1


def test_motivo_e_a_menor_regra_quando_ha_duas(session, carregado):
    # a solicitação duplicada (PRE-20) que também tem desistência (PRE-23)
    duplas = session.exec(text(
        "select s.solicitacao_id from solicitacoes s where s.status_fila='suspensa' and exists "
        "(select 1 from pendencias a where a.solicitacao_id=s.solicitacao_id and a.regra='PRE-20') and exists "
        "(select 1 from pendencias b where b.solicitacao_id=s.solicitacao_id and b.regra in ('PRE-21','PRE-22','PRE-23','PRE-25'))"
    )).all()

    assert duplas
    for (sol_id,) in duplas:
        assert solicitacao(session, sol_id).motivo_status == "PRE-20"


def test_post_admin_carga_traz_os_bloqueantes(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        resp = TestClient(app).post("/admin/carga")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["bloqueantes"] == {
        "solicitacoes": 941, "achados": ACHADOS, "suspensas": 41, "reativadas": 0,
        "oncologicas_a_confirmar": 5, "eventos_orfaos": 9,
        "pendencias": {"abertas": 56, "atualizadas": 0, "encerradas": 0},
    }
