"""Configuração central. Valores podem ser sobrescritos por variáveis de ambiente (prefixo HP_)."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    output_dir: Path
    db_url: str
    verificador_path: Path
    ref_date: date
    use_mocks: bool


def _load() -> Settings:
    backend_dir = REPO_ROOT / "backend"
    return Settings(
        data_dir=Path(os.getenv("HP_DATA_DIR", REPO_ROOT / "data")),
        output_dir=Path(os.getenv("HP_OUTPUT_DIR", backend_dir / "output")),
        # Defaults batem com o docker-compose.yml da raiz.
        db_url=os.getenv("HP_DB_URL",
                         "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior"),
        verificador_path=REPO_ROOT / "src" / "verificar_fila_priorizada.py",
        # Data de referência do dataset. Nunca use date.today() nas regras.
        ref_date=date.fromisoformat(os.getenv("HP_REF_DATE", "2026-10-23")),
        # Enquanto os casos de uso não existem, a API devolve mocks com o contrato final.
        use_mocks=os.getenv("HP_USE_MOCKS", "true").lower() == "true",
    )


settings = _load()
