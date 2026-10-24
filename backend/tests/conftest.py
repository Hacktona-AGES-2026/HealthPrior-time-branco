import os

os.environ.setdefault("HP_USE_MOCKS", "true")

import pytest
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, create_engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior_test",
)


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


@pytest.fixture
def session(_engine):
    """Banco de teste vazio a cada teste."""
    SQLModel.metadata.drop_all(_engine)
    SQLModel.metadata.create_all(_engine)
    with Session(_engine) as s:
        yield s
    SQLModel.metadata.drop_all(_engine)
