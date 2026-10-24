from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app import config
from app.models import Base


@lru_cache(maxsize=None)
def get_engine(url: str = config.DATABASE_URL) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def init_db(engine: Engine) -> None:
    """Cria as tabelas que ainda não existem (idempotente)."""
    Base.metadata.create_all(engine)
