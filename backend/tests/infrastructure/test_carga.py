"""US-01 · carga inicial com o dataset real (precisa do Postgres de teste)."""
import csv
import shutil
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import func, select, text

from app.application.carga_inicial import CargaInicial
from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.repositories import SqlCargaRepository
from app.infrastructure.tables import EventoTable, ProcedimentoTable, SolicitacaoTable
from app.main import app

DATA = settings.data_dir
ARQUIVOS = [
    ("procedimentos.csv", ProcedimentoTable),
    ("fila_cirurgica.csv", SolicitacaoTable),
    ("eventos_clinicos.csv", EventoTable),
]


def carregar(session, data_dir=DATA):
    return CargaInicial(LeitorDataset(data_dir), SqlCargaRepository(session)).executar()


def contar(session, tabela):
    return session.exec(select(func.count()).select_from(tabela)).one()


def test_conta_registros_do_dataset(session):
    r = carregar(session)

    assert (r.procedimentos.inseridos, r.solicitacoes.inseridos, r.eventos.inseridos) == (23, 941, 1505)
    assert (contar(session, ProcedimentoTable), contar(session, SolicitacaoTable),
            contar(session, EventoTable)) == (23, 941, 1505)


def test_e_idempotente(session):
    carregar(session)
    r = carregar(session)

    assert (r.procedimentos.inseridos, r.solicitacoes.inseridos, r.eventos.inseridos) == (0, 0, 0)
    assert r.solicitacoes.atualizados == 941
    assert (contar(session, ProcedimentoTable), contar(session, SolicitacaoTable),
            contar(session, EventoTable)) == (23, 941, 1505)


def test_valores_originais_preservados(session):
    """Cada célula do CSV volta igual do banco (vazio vira NULL)."""
    carregar(session)

    for arquivo, tabela in ARQUIVOS:
        pk = tabela.__table__.primary_key.columns.keys()[0]
        with (DATA / arquivo).open(encoding="utf-8", newline="") as f:
            do_csv = {r[pk]: r for r in csv.DictReader(f)}
        do_banco = {getattr(o, pk): o for o in session.exec(select(tabela)).all()}
        assert do_banco.keys() == do_csv.keys()
        for chave, linha in do_csv.items():
            for coluna, bruto in linha.items():
                obtido = getattr(do_banco[chave], coluna)
                if bruto == "":
                    assert obtido is None, (arquivo, chave, coluna)
                elif isinstance(obtido, date):
                    assert obtido.isoformat() == bruto, (arquivo, chave, coluna)
                elif isinstance(obtido, float):
                    assert obtido == float(bruto), (arquivo, chave, coluna)
                else:
                    assert str(obtido) == bruto, (arquivo, chave, coluna)


def test_nao_confirma_classe_na_carga(session):
    carregar(session)

    pares = session.exec(select(SolicitacaoTable.classe_status, SolicitacaoTable.status_fila).distinct()).all()
    assert pares == [("sugerida_nao_confirmada", "ativa")]


def test_recarga_preserva_estado_do_sistema(session):
    carregar(session)
    session.exec(text("update solicitacoes set status_fila='suspensa', classe_status='confirmada' "
                      "where solicitacao_id='SOL-2024-00076'"))
    session.commit()

    carregar(session)

    s = session.get(SolicitacaoTable, "SOL-2024-00076")
    assert (s.status_fila, s.classe_status) == ("suspensa", "confirmada")


def test_valores_sujos_nao_sao_corrigidos_na_carga(session):
    """Normalização é da US-02: o CID entra com e sem ponto, como veio."""
    carregar(session)

    cids = set(session.exec(select(SolicitacaoTable.cid_principal).distinct()).all())
    assert "C18.7" in cids
    assert any("." not in c for c in cids)


def test_evento_orfao_e_mantido(session):
    carregar(session)

    orfao = session.exec(text(
        "select e.solicitacao_id from eventos e left join solicitacoes s using (solicitacao_id) "
        "where e.evento_id='EVT-000287' and s.solicitacao_id is null")).first()
    assert orfao is not None


def test_arquivo_ausente(session, tmp_path):
    with pytest.raises(CargaInvalidaError, match="não encontrado"):
        carregar(session, tmp_path)


def test_colunas_inesperadas_nao_carregam_nada(session, tmp_path):
    for arquivo, _ in ARQUIVOS:
        shutil.copy(DATA / arquivo, tmp_path / arquivo)
    quebrado = (tmp_path / "eventos_clinicos.csv").read_text(encoding="utf-8").replace("origem", "fonte", 1)
    (tmp_path / "eventos_clinicos.csv").write_text(quebrado, encoding="utf-8")

    with pytest.raises(CargaInvalidaError, match="colunas inesperadas"):
        carregar(session, tmp_path)
    assert contar(session, SolicitacaoTable) == 0


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_post_admin_carga(client):
    primeira = client.post("/admin/carga")
    segunda = client.post("/admin/carga")

    assert primeira.status_code == 200
    assert primeira.json()["solicitacoes"] == {"lido": 941, "inseridos": 941, "atualizados": 0}
    assert segunda.json()["solicitacoes"] == {"lido": 941, "inseridos": 0, "atualizados": 941}


def test_post_admin_carga_com_arquivo_ausente(client, monkeypatch, tmp_path):
    monkeypatch.setattr(LeitorDataset, "__init__", lambda self, data_dir=None: setattr(self, "data_dir", tmp_path))

    resp = client.post("/admin/carga")

    assert resp.status_code == 422
    assert resp.json()["erro"] == "CARGA_INVALIDA"
