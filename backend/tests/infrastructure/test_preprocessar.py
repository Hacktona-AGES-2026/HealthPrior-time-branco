"""US-03 · flags recalculadas e eventos limpos, com o dataset real (precisa do Postgres de teste)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select, text

from app.application.carga_inicial import CargaInicial
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.tables import CorrecaoTable, EventoTable, SolicitacaoTable
from app.main import app

DATA = settings.data_dir


REGRAS_US03 = ("PRE-05", "PRE-06")


def recalcular(session) -> RecalcularFlags:
    return RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           SqlCorrecaoRepository(session))


def carregar(session, com_flags=True):
    """A carga como o CLI faz: normaliza e recalcula as flags na mesma transação."""
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    return CargaInicial(LeitorDataset(DATA), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session),
                        recalcular(session) if com_flags else None).executar()


def reprocessar(session):
    """O comando avulso `flags`: recalcula e confirma."""
    resumo = recalcular(session).executar()
    SqlUnidadeDeTrabalho(session).confirmar()
    return resumo


@pytest.fixture
def carregado(_dataset_carregado):
    """Carga feita uma vez por módulo (conftest); `session` aponta para esse banco."""
    return _dataset_carregado[1].flags


def correcoes_por_regra(session):
    """Só as regras da US-03 (a normalização, US-02, também escreve no mesmo log)."""
    linhas = session.exec(select(CorrecaoTable.regra, func.count()).group_by(CorrecaoTable.regra)).all()
    return {regra: n for regra, n in linhas if regra in REGRAS_US03}


def eventos_de(session, sol_id):
    return {e.evento_id: e for e in session.exec(
        select(EventoTable).where(EventoTable.solicitacao_id == sol_id)).all()}


def test_resumo_do_dataset(carregado):
    assert carregado.solicitacoes == 941
    assert carregado.eventos_duplicados == 6
    assert carregado.eventos_historicos == 155
    assert carregado.correcoes == {"PRE-05": 44, "PRE-06": 147}


def test_oncologico_vem_do_cid_e_nao_da_flag(session, carregado):
    c61 = session.get(SolicitacaoTable, "SOL-2025-00149")
    assert (c61.flag_oncologico, c61.oncologico) == ("nao", True)
    hernia = session.get(SolicitacaoTable, "SOL-2026-00583")
    assert (hernia.flag_oncologico, hernia.oncologico) == ("sim", False)
    benigna = session.get(SolicitacaoTable, "SOL-2025-00196")  # D24 com flag "sim"
    assert (benigna.flag_oncologico, benigna.oncologico) == ("sim", False)
    assert session.get(SolicitacaoTable, "SOL-2023-00010").oncologico is True


def test_177_oncologicos_pelo_cid(session, carregado):
    total = session.exec(select(func.count()).select_from(SolicitacaoTable)
                         .where(SolicitacaoTable.oncologico)).one()
    assert total == 177


def test_flags_originais_continuam_no_banco(session, carregado):
    assert session.get(SolicitacaoTable, "SOL-2025-00149").flag_oncologico == "nao"
    sim = session.exec(select(func.count()).select_from(SolicitacaoTable)
                       .where(SolicitacaoTable.flag_piora_clinica == "sim")).one()
    assert sim == 88


def test_correcao_registra_campo_original_novo_e_regra(session, carregado):
    c = session.exec(select(CorrecaoTable).where(CorrecaoTable.solicitacao_id == "SOL-2025-00149",
                                                 CorrecaoTable.regra == "PRE-05")).one()

    assert (c.campo, c.original, c.novo, c.regra) == ("flag_oncologico", "nao", "sim", "PRE-05")


def test_evento_duplicado_aponta_para_o_original(session, carregado):
    eventos = eventos_de(session, "SOL-2023-00083")

    assert eventos["EVT-000050"].duplicado_de is None
    assert eventos["EVT-000051"].duplicado_de == "EVT-000050"


def test_nenhum_evento_e_apagado(session, carregado):
    assert session.exec(select(func.count()).select_from(EventoTable)).one() == 1505


def test_evento_000712_e_713_continuam_dois_atendimentos(session, carregado):
    # mesma solicitação e descrição, mas origens diferentes (D-30)
    e712 = session.get(EventoTable, "EVT-000712")
    e713 = session.get(EventoTable, "EVT-000713")

    assert (e712.duplicado_de, e713.duplicado_de) == (None, None)


def test_sol_2023_00017_tem_2_ps_em_historico(session, carregado):
    eventos = eventos_de(session, "SOL-2023-00017").values()

    ps = [e for e in eventos if e.tipo_evento == "pronto_socorro"]
    assert len(ps) == 2 and all(e.historico for e in ps)
    assert not any(e.historico for e in eventos if e.tipo_evento != "pronto_socorro")


def test_ps_historico_nao_conta_como_piora(session, carregado):
    # só têm PS anterior à entrada e flag original "nao"
    for sol_id in ("SOL-2026-00505", "SOL-2025-00287", "SOL-2025-00109"):
        assert session.get(SolicitacaoTable, sol_id).piora_recalculada is False, sol_id


def test_evento_orfao_nao_e_historico_nem_duplicado(session, carregado):
    e = session.get(EventoTable, "EVT-000287")

    assert (e.historico, e.duplicado_de) == (False, None)


def test_flag_sim_nunca_e_rebaixada(session, carregado):
    rebaixadas = session.exec(select(func.count()).select_from(SolicitacaoTable).where(
        SolicitacaoTable.flag_piora_clinica == "sim", SolicitacaoTable.piora_recalculada.is_not(True))).one()

    assert rebaixadas == 0


def test_reprocessar_e_idempotente(session, carregado):
    antes = correcoes_por_regra(session)

    resumo = reprocessar(session)

    assert correcoes_por_regra(session) == antes == {"PRE-05": 44, "PRE-06": 147}
    assert (resumo.eventos_duplicados, resumo.eventos_historicos) == (6, 155)


def test_reprocessar_nao_apaga_log_de_outras_regras(session, carregado):
    session.exec(text("insert into correcoes_log (solicitacao_id, campo, original, novo, regra, criado_em) "
                      "values ('SOL-2025-00149', 'x', 'a', 'b', 'PRE-20', now())"))
    session.commit()

    reprocessar(session)

    assert session.exec(text("select count(*) from correcoes_log where regra = 'PRE-20'")).one()[0] == 1


def test_recarga_do_dataset_refaz_as_marcas_sem_duplicar(session):
    carregar(session)
    resumo = carregar(session)

    assert resumo.flags.correcoes == {"PRE-05": 44, "PRE-06": 147}
    assert correcoes_por_regra(session) == {"PRE-05": 44, "PRE-06": 147}


def test_post_admin_carga_traz_as_flags(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        resp = TestClient(app).post("/admin/carga")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["flags"] == {
        "solicitacoes": 941, "eventos_duplicados": 6, "eventos_historicos": 155,
        "correcoes": {"PRE-05": 44, "PRE-06": 147},
    }
