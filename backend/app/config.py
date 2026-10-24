"""Configuração central. Valores podem ser sobrescritos por variáveis de ambiente (prefixo HP_)."""
import os
from dataclasses import dataclass, field
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


def _url_do_banco() -> str:
    """`HP_DB_URL` (ou `DATABASE_URL`, como Render e Neon entregam). `postgres://` e `postgresql://` viram o driver psycopg 3."""
    url = os.getenv("HP_DB_URL") or os.getenv("DATABASE_URL") or \
        "postgresql+psycopg://healthprior:healthprior@localhost:5432/healthprior"  # bate com o docker-compose.yml
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


def _origens_cors() -> tuple[str, ...]:
    """Front local mais as origens de `HP_CORS_ORIGINS` (separadas por vírgula; ex.: o domínio da Vercel)."""
    extras = tuple(o.strip().rstrip("/") for o in os.getenv("HP_CORS_ORIGINS", "").split(",") if o.strip())
    return ("http://localhost:5173", "http://127.0.0.1:5173", *extras)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    output_dir: Path
    db_url: str
    cors_origins: tuple[str, ...]
    verificador_path: Path
    ref_date: date
    use_mocks: bool
    openrouter_api_key: str
    llm_model: str
    llm_enabled: bool
    llm_cache_path: Path
    recontato_dias: int
    # Notificações ao paciente (demo). Canal real só com HP_NOTIFICA_CANAL=twilio e as credenciais no .env.
    notifica_canal: str
    notifica_destino: str  # número da demo: nunca o do paciente
    notifica_limite_envio: int  # no máximo, por rodada de envio
    notifica_min_posicoes: int  # só avisa quem mudou tantas posições
    notifica_max_por_publicacao: int
    twilio_account_sid: str
    twilio_from: str
    twilio_api_key_sid: str
    twilio_sms_template: str
    ntfy_url: str
    ntfy_topic: str
    waha_url: str
    waha_session: str
    twilio_auth_token: str = field(repr=False)
    twilio_api_key_secret: str = field(repr=False)
    ntfy_token: str = field(repr=False)
    waha_api_key: str = field(repr=False)
    fatores_enabled: bool
    irr_path: Path
    cid_llm_model: str
    cid_llm_esforco: str
    cid_llm_cache_path: Path


def _load() -> Settings:
    backend_dir = REPO_ROOT / "backend"
    return Settings(
        data_dir=Path(os.getenv("HP_DATA_DIR", REPO_ROOT / "data")),
        output_dir=Path(os.getenv("HP_OUTPUT_DIR", backend_dir / "output")),
        db_url=_url_do_banco(),
        cors_origins=_origens_cors(),
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
        # Q-04 (provisório): dias sem evento até pedir o recontato (C-04).
        recontato_dias=int(os.getenv("HP_RECONTATO_DIAS", "180")),
        notifica_canal=os.getenv("HP_NOTIFICA_CANAL", "simulado").strip().lower(),
        notifica_destino=os.getenv("HP_NOTIFICA_DESTINO", "").strip(),
        notifica_limite_envio=int(os.getenv("HP_NOTIFICA_LIMITE_ENVIO", "5")),
        notifica_min_posicoes=int(os.getenv("HP_NOTIFICA_MIN_POSICOES", "20")),
        notifica_max_por_publicacao=int(os.getenv("HP_NOTIFICA_MAX_POR_PUBLICACAO", "3")),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
        twilio_from=os.getenv("TWILIO_FROM", "").strip(),
        twilio_api_key_sid=os.getenv("TWILIO_API_KEY_SID", "").strip(),
        twilio_sms_template=os.getenv("TWILIO_SMS_TEMPLATE", "").strip(),
        ntfy_url=os.getenv("NTFY_URL", "https://ntfy.sh").strip().rstrip("/"),
        ntfy_topic=os.getenv("NTFY_TOPIC", "").strip(),
        waha_url=os.getenv("WAHA_URL", "http://localhost:3000").strip().rstrip("/"),
        waha_session=os.getenv("WAHA_SESSION", "default").strip() or "default",
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
        twilio_api_key_secret=os.getenv("TWILIO_API_KEY_SECRET", "").strip(),
        ntfy_token=os.getenv("NTFY_TOKEN", "").strip(),
        waha_api_key=os.getenv("WAHA_API_KEY", "").strip(),
        # Fatores de comorbidade e idade/IRR no score (domain/fatores.py).
        fatores_enabled=os.getenv("HP_FATORES_ENABLED", "true").lower() == "true",
        irr_path=Path(os.getenv("HP_IRR_PATH", REPO_ROOT / "score" / "references"
                                / "irr_nacional_cid_idade_2019_2023.csv")),
        # Sugestão de CID a partir do laudo (PRE-12, D-125). Esforço "low": mais rápido, mesmo CID.
        cid_llm_model=os.getenv("HP_CID_LLM_MODEL", "openai/gpt-6-luna"),
        cid_llm_esforco=os.getenv("HP_CID_LLM_ESFORCO", "low"),
        cid_llm_cache_path=Path(os.getenv("HP_CID_LLM_CACHE",
                                          REPO_ROOT / "data" / "processed" / "cache_cid_llm.json")),
    )


settings = _load()
