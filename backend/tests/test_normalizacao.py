"""Normalização no banco (US-02) com o dataset real."""
from sqlalchemy import func, select, text

from app import config
from app.loader import carga
from app.models import CorrecaoLog, Solicitacao
from app.normalization import normalizar

DATA = config.DATA_DIR


def valores(engine, coluna):
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(select(coluna))]


def contagem_por_regra(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            select(CorrecaoLog.regra, func.count()).group_by(CorrecaoLog.regra)
        ).all()
    return dict(rows)


def test_carga_normaliza_as_quatro_colunas(engine):
    r = carga(engine, DATA).normalizacao

    assert r.solicitacoes == 941
    with engine.connect() as conn:
        sem_norm = conn.execute(
            select(func.count()).where(
                Solicitacao.cid_norm.is_(None) | Solicitacao.nome_norm.is_(None)
                | Solicitacao.municipio_norm.is_(None)
            )
        ).scalar()
    assert sem_norm == 0


def test_cid_norm_sem_ponto_e_maiusculo(engine):
    carga(engine, DATA)

    cids = valores(engine, Solicitacao.cid_norm)
    assert all("." not in c and c == c.upper() for c in cids)
    assert len(set(cids)) < len(set(valores(engine, Solicitacao.cid_principal)))  # K42.9 e K429 juntos


def test_municipios_unificados_pelo_nome_oficial(engine):
    carga(engine, DATA)

    brutos = set(valores(engine, Solicitacao.municipio))
    normalizados = set(valores(engine, Solicitacao.municipio_norm))
    assert {"PORTO ALEGRE", "porto alegre", "Porto Alegre"} <= brutos
    assert len(brutos) == 62 and len(normalizados) == 38
    assert {"Porto Alegre", "Gravataí", "Osório"} <= normalizados


def test_prioridade_norm_so_tem_tres_valores_ou_vazio(engine):
    carga(engine, DATA)

    prioridades = valores(engine, Solicitacao.prioridade_norm)
    assert set(prioridades) == {"alta", "media", "baixa", None}
    assert prioridades.count(None) == 11  # PRE-15: 11 sem prioridade


def test_pac_00087_tem_o_mesmo_nome_norm_nas_duas_grafias(engine):
    carga(engine, DATA)

    with engine.connect() as conn:
        rows = conn.execute(
            select(Solicitacao.nome_paciente, Solicitacao.nome_norm).where(
                Solicitacao.paciente_id == "PAC-00087"
            )
        ).all()
    assert {r[0] for r in rows} >= {"Jurema Quadros Weber", "JUREMA QUADROS WEBER"}
    assert len({r[1] for r in rows}) == 1


def test_originais_continuam_intactos(engine):
    carga(engine, DATA)

    with engine.connect() as conn:
        grafias_originais = conn.execute(
            select(func.count()).where(Solicitacao.prioridade_regulacao.in_(["Baixa", "Média", "Alta"]))
        ).scalar()
    assert grafias_originais == 23
    assert "K429" in valores(engine, Solicitacao.cid_principal)  # sem ponto, como veio


def test_log_registra_campo_original_novo_e_regra(engine):
    carga(engine, DATA)

    with engine.connect() as conn:
        entradas = conn.execute(
            select(CorrecaoLog.campo, CorrecaoLog.original, CorrecaoLog.novo, CorrecaoLog.regra)
            .where(CorrecaoLog.original.in_(["PORTO ALEGRE", "Média"]))
        ).all()
    assert ("municipio", "PORTO ALEGRE", "Porto Alegre", "PRE-03") in entradas
    assert ("prioridade_regulacao", "Média", "media", "PRE-04") in entradas


def test_log_por_regra_no_dataset(engine):
    carga(engine, DATA)

    por_regra = contagem_por_regra(engine)
    assert por_regra["PRE-04"] == 23  # 13 Baixa + 7 Média + 3 Alta
    assert "PRE-02" not in por_regra and "PRE-01" not in por_regra  # D-17


def test_normalizar_e_idempotente(engine):
    carga(engine, DATA)
    antes = contagem_por_regra(engine)

    carga(engine, DATA)
    with engine.begin() as conn:
        normalizar(conn)

    assert contagem_por_regra(engine) == antes
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(CorrecaoLog)).scalar() == sum(antes.values())


def test_normalizar_nao_apaga_log_de_outras_regras(engine):
    carga(engine, DATA)
    with engine.begin() as conn:
        conn.execute(
            text("insert into correcoes_log (solicitacao_id, campo, original, novo, regra) "
                 "values ('SOL-2025-00149', 'flag_oncologico', 'nao', 'sim', 'PRE-05')")
        )

    with engine.begin() as conn:
        normalizar(conn)

    assert contagem_por_regra(engine)["PRE-05"] == 1
