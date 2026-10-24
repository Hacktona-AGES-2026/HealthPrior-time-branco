import os

os.environ.setdefault("HP_USE_MOCKS", "true")

import pytest
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, create_engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior_test",
)
# pytest-xdist (-n): um banco por worker, senão o drop_all de um apaga as tabelas do outro.
_WORKER = os.environ.get("PYTEST_XDIST_WORKER")
if _WORKER:
    _url = make_url(TEST_DATABASE_URL)
    TEST_DATABASE_URL = _url.set(database=f"{_url.database}_{_WORKER}").render_as_string(
        hide_password=False)


def _garantir_banco(url: str) -> None:
    alvo = make_url(url)
    admin = create_engine(alvo.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        existe = conn.execute(text("select 1 from pg_database where datname = :n"),
                              {"n": alvo.database}).scalar()
        if not existe:
            conn.execute(text(f'create database "{alvo.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def _engine():
    try:
        _garantir_banco(TEST_DATABASE_URL)
    except Exception as e:  # Postgres fora do ar: avisa em vez de falhar com stack trace
        pytest.skip(f"Postgres de teste indisponível ({e.__class__.__name__}); rode `docker compose up -d`")
    from app.infrastructure import tables  # noqa: F401  (registra os modelos)

    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def _dataset_carregado(_engine, request):
    """Dataset carregado uma vez por módulo, com o `carregar(session)` do próprio módulo.

    Fica num banco à parte (<teste>_carregado) para não disputar lock com o `session` vazio.
    Devolve (engine, resumo da carga). Os testes nunca confirmam nada nele (ver `session`).
    """
    url = make_url(TEST_DATABASE_URL)
    url = url.set(database=f"{url.database}_carregado").render_as_string(hide_password=False)
    _garantir_banco(url)
    engine = create_engine(url)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        resumo = request.module.carregar(s)
    yield engine, resumo
    engine.dispose()


@pytest.fixture
def session(request, _engine):
    """Banco de teste vazio a cada teste.

    Se o teste usa a fixture `carregado`, recebe o banco com o dataset já carregado, dentro de
    uma transação desfeita no fim: `commit()` no teste só libera um savepoint
    (join_transaction_mode="create_savepoint"), então o próximo teste vê o banco intacto.
    """
    if "carregado" in request.fixturenames:
        engine, _ = request.getfixturevalue("_dataset_carregado")
        with engine.connect() as conn:
            transacao = conn.begin()
            with Session(bind=conn, join_transaction_mode="create_savepoint") as s:
                yield s
            transacao.rollback()
        return
    SQLModel.metadata.drop_all(_engine)
    SQLModel.metadata.create_all(_engine)
    with Session(_engine) as s:
        yield s
    SQLModel.metadata.drop_all(_engine)
