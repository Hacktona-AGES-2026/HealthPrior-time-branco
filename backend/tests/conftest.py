import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.models import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior_test",
)


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("select 1 from pg_database where datname = :n"), {"n": target.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'create database "{target.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def _engine():
    try:
        _ensure_database(TEST_DATABASE_URL)
    except Exception as e:  # Postgres fora do ar: avisa em vez de falhar com stack trace
        pytest.skip(f"Postgres de teste indisponível ({e.__class__.__name__}); rode `docker compose up -d`")
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(_engine):
    """Banco de teste vazio a cada teste."""
    Base.metadata.drop_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
