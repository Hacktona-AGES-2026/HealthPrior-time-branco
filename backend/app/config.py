"""Configuração central. Valores podem ser sobrescritos por variáveis de ambiente (prefixo HP_)."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _carregar_dotenv(caminho: Path) -> None:
    """Lê KEY=valor do .env da raiz sem sobrescrever o ambiente (segredos ficam fora do código)."""
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        chave, sep, valor = linha.strip().partition("=")
        if sep and not chave.startswith("#"):
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    output_dir: Path
    db_url: str
    verificador_path: Path
    ref_date: date
    use_mocks: bool
    openrouter_api_key: str
    llm_model: str
    llm_enabled: bool
    llm_cache_path: Path
    fatores_enabled: bool
    irr_path: Path


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
        # Extração de sinais do texto por LLM (OpenRouter). Sem chave, só palavra-chave.
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        llm_model=os.getenv("HP_LLM_MODEL", "typesafe/jev-1.14"),
        llm_enabled=os.getenv("HP_LLM_ENABLED", "true").lower() == "true",
        llm_cache_path=Path(os.getenv("HP_LLM_CACHE", REPO_ROOT / "data" / "processed" / "cache_llm.json")),
        # Fatores de comorbidade e idade/IRR no score (domain/fatores.py).
        fatores_enabled=os.getenv("HP_FATORES_ENABLED", "true").lower() == "true",
        irr_path=Path(os.getenv("HP_IRR_PATH", REPO_ROOT / "score" / "references"
                                / "irr_nacional_cid_idade_2019_2023.csv")),
    )


settings = _load()
