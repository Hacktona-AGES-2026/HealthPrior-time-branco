"""Conexão com o banco (PostgreSQL via SQLModel; ver D-15)."""
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.db_url, pool_pre_ping=True)


def criar_tabelas() -> None:
    from app.infrastructure import tables  # noqa: F401  (registra os modelos)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
