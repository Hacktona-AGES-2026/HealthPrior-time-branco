import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Os defaults batem com o docker-compose.yml da raiz.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior",
)
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO_ROOT / "data"))

# Data de referência fixa do desafio (nunca usar today()).
REF = "2026-10-23"
