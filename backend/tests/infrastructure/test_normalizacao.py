"""Normalização no banco (US-02) com o dataset real (precisa do Postgres de teste)."""
from sqlmodel import func, select

from app.application.carga_inicial import CargaInicial
from app.application.normalizar import Normalizar
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.tables import CorrecaoTable, SolicitacaoTable

DATA = settings.data_dir


def normalizador(session):
    return Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))


def carregar(session):
    return CargaInicial(LeitorDataset(DATA), SqlCargaRepository(session), normalizador(session),
                        SqlUnidadeDeTrabalho(session)).executar()


def valores(session, coluna):
    return list(session.exec(select(coluna)).all())


def por_regra(session):
    return dict(session.exec(select(CorrecaoTable.regra, func.count()).group_by(CorrecaoTable.regra)).all())


def test_carga_normaliza_as_quatro_colunas(session):
    r = carregar(session).normalizacao

    assert r.solicitacoes == 941
    sem_norm = session.exec(select(func.count()).where(
        (SolicitacaoTable.cid_norm == "") | (SolicitacaoTable.nome_norm.is_(None))
        | (SolicitacaoTable.nome_norm == "") | SolicitacaoTable.municipio_norm.is_(None)
    )).one()
    assert sem_norm == 0


def test_cid_norm_sem_ponto_e_maiusculo(session):
    carregar(session)

    cids = valores(session, SolicitacaoTable.cid_norm)
    assert all("." not in c and c == c.upper() for c in cids)
    assert len(set(cids)) < len(set(valores(session, SolicitacaoTable.cid_principal)))  # K42.9 e K429 juntos


def test_municipios_unificados_pelo_nome_oficial(session):
    carregar(session)

    brutos = set(valores(session, SolicitacaoTable.municipio))
    normalizados = set(valores(session, SolicitacaoTable.municipio_norm))
    assert {"PORTO ALEGRE", "porto alegre", "Porto Alegre"} <= brutos
    assert len(brutos) == 62 and len(normalizados) == 38
    assert {"Porto Alegre", "Gravataí", "Osório"} <= normalizados


def test_prioridade_norm_so_tem_tres_valores_ou_vazio(session):
    carregar(session)

    prioridades = valores(session, SolicitacaoTable.prioridade_norm)
    assert set(prioridades) == {"alta", "media", "baixa", None}
    assert prioridades.count(None) == 11  # PRE-15: 11 sem prioridade


def test_pac_00087_tem_o_mesmo_nome_norm_nas_duas_grafias(session):
    carregar(session)

    linhas = session.exec(select(SolicitacaoTable.nome_paciente, SolicitacaoTable.nome_norm)
                          .where(SolicitacaoTable.paciente_id == "PAC-00087")).all()
    assert {n for n, _ in linhas} >= {"Jurema Quadros Weber", "JUREMA QUADROS WEBER"}
    assert len({norm for _, norm in linhas}) == 1


def test_originais_continuam_intactos(session):
    carregar(session)

    grafias = session.exec(select(func.count()).where(
        SolicitacaoTable.prioridade_regulacao.in_(["Baixa", "Média", "Alta"]))).one()
    assert grafias == 23
    assert "K429" in valores(session, SolicitacaoTable.cid_principal)  # sem ponto, como veio


def test_log_registra_campo_original_novo_e_regra(session):
    carregar(session)

    entradas = session.exec(select(CorrecaoTable.campo, CorrecaoTable.original, CorrecaoTable.novo,
                                   CorrecaoTable.regra)
                            .where(CorrecaoTable.original.in_(["PORTO ALEGRE", "Média"]))).all()
    assert ("municipio", "PORTO ALEGRE", "Porto Alegre", "PRE-03") in entradas
    assert ("prioridade_regulacao", "Média", "media", "PRE-04") in entradas


def test_log_por_regra_no_dataset(session):
    carregar(session)

    regras = por_regra(session)
    assert regras["PRE-04"] == 23  # 13 Baixa + 7 Média + 3 Alta
    assert "PRE-02" not in regras and "PRE-01" not in regras  # D-18


def test_normalizar_e_idempotente(session):
    carregar(session)
    antes = por_regra(session)

    carregar(session)
    normalizador(session).executar()
    session.commit()

    assert por_regra(session) == antes
    assert session.exec(select(func.count()).select_from(CorrecaoTable)).one() == sum(antes.values())


def test_normalizar_nao_apaga_log_de_outras_regras(session):
    carregar(session)
    session.add(CorrecaoTable(solicitacao_id="SOL-2025-00149", campo="flag_oncologico", original="nao",
                              novo="sim", regra="PRE-05"))
    session.commit()

    normalizador(session).executar()
    session.commit()

    assert por_regra(session)["PRE-05"] == 1


def test_falha_na_normalizacao_desfaz_a_carga(session, monkeypatch):
    def falha(self):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(Normalizar, "executar", falha)

    try:
        carregar(session)
    except RuntimeError:
        pass

    assert session.exec(select(func.count()).select_from(SolicitacaoTable)).one() == 0
