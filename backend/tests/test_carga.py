import csv
import shutil
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app import config, main
from app.loader import SOURCES, CargaError, carga
from app.models import Evento, Procedimento, Solicitacao

DATA = config.DATA_DIR


def count(engine, model):
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(model)).scalar()


def test_carga_conta_registros_do_dataset(engine):
    r = carga(engine, DATA)

    assert (r["procedimentos"].inseridos, r["solicitacoes"].inseridos, r["eventos"].inseridos) == (23, 941, 1505)
    assert count(engine, Procedimento) == 23
    assert count(engine, Solicitacao) == 941
    assert count(engine, Evento) == 1505


def test_carga_e_idempotente(engine):
    carga(engine, DATA)
    r = carga(engine, DATA)

    assert all(t.inseridos == 0 for t in r.values())
    assert count(engine, Solicitacao) == 941
    assert count(engine, Evento) == 1505
    assert count(engine, Procedimento) == 23


def test_valores_originais_preservados(engine):
    """Cada célula do CSV volta igual do banco (vazio vira NULL)."""
    carga(engine, DATA)

    for _, filename, model in SOURCES:
        pk = model.__table__.primary_key.columns.keys()[0]
        with (DATA / filename).open(encoding="utf-8", newline="") as f:
            csv_rows = {r[pk]: r for r in csv.DictReader(f)}
        with engine.connect() as conn:
            db_rows = {r[pk]: r for r in conn.execute(select(model)).mappings()}
        assert db_rows.keys() == csv_rows.keys()
        for key, raw_row in csv_rows.items():
            for col, raw in raw_row.items():
                got = db_rows[key][col]
                if raw == "":
                    assert got is None, (filename, key, col)
                elif isinstance(got, date):
                    assert got.isoformat() == raw, (filename, key, col)
                elif isinstance(got, Decimal):
                    assert got == Decimal(raw), (filename, key, col)
                else:
                    assert str(got) == raw, (filename, key, col)


def test_carga_inicial_nao_confirma_classe(engine):
    carga(engine, DATA)

    with engine.connect() as conn:
        rows = conn.execute(
            select(Solicitacao.classe_status, Solicitacao.status_fila).distinct()
        ).all()
    assert rows == [("sugerida_nao_confirmada", "ativa")]


def test_recarga_preserva_estado_do_sistema(engine):
    carga(engine, DATA)
    with engine.begin() as conn:
        conn.execute(
            text("update solicitacoes set status_fila='suspensa', classe_status='confirmada' "
                 "where solicitacao_id='SOL-2024-00076'")
        )

    carga(engine, DATA)

    with engine.connect() as conn:
        row = conn.execute(
            select(Solicitacao.status_fila, Solicitacao.classe_status).where(
                Solicitacao.solicitacao_id == "SOL-2024-00076"
            )
        ).one()
    assert row == ("suspensa", "confirmada")


def test_valores_sujos_nao_sao_corrigidos_na_carga(engine):
    """Normalização é da US-02: a carga guarda o CID com e sem ponto como veio."""
    carga(engine, DATA)

    with engine.connect() as conn:
        cids = {r[0] for r in conn.execute(select(Solicitacao.cid_principal).distinct())}
    assert "C18.7" in cids
    assert any("." not in c for c in cids)


def test_evento_orfao_e_mantido(engine):
    carga(engine, DATA)

    with engine.connect() as conn:
        orfao = conn.execute(
            text("select e.solicitacao_id from eventos e left join solicitacoes s "
                 "using (solicitacao_id) where e.evento_id='EVT-000287' and s.solicitacao_id is null")
        ).first()
    assert orfao is not None


def test_arquivo_ausente(engine, tmp_path):
    with pytest.raises(CargaError, match="não encontrado"):
        carga(engine, tmp_path)


def test_colunas_inesperadas_nao_carregam_nada(engine, tmp_path):
    for _, filename, _ in SOURCES:
        shutil.copy(DATA / filename, tmp_path / filename)
    broken = (tmp_path / "eventos_clinicos.csv").read_text(encoding="utf-8").replace("origem", "fonte", 1)
    (tmp_path / "eventos_clinicos.csv").write_text(broken, encoding="utf-8")

    with pytest.raises(CargaError, match="colunas inesperadas"):
        carga(engine, tmp_path)
    assert count(engine, Solicitacao) == 0


def test_post_admin_carga(engine, monkeypatch):
    monkeypatch.setattr(main, "get_engine", lambda: engine)
    client = TestClient(main.app)

    first = client.post("/admin/carga")
    second = client.post("/admin/carga")

    assert first.status_code == 200
    assert first.json()["solicitacoes"] == {"lido": 941, "inseridos": 941, "atualizados": 0}
    assert second.json()["solicitacoes"] == {"lido": 941, "inseridos": 0, "atualizados": 941}


def test_post_admin_carga_com_arquivo_ausente(engine, monkeypatch, tmp_path):
    monkeypatch.setattr(main, "get_engine", lambda: engine)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    client = TestClient(main.app)

    resp = client.post("/admin/carga")

    assert resp.status_code == 422
    assert resp.json()["erro"] == "CARGA_INVALIDA"
