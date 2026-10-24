"""Normalização automática (US-02, regras PRE-01..PRE-04 de docs/fluxo-sistema.md C-05).

Funções puras: sem banco, sem relógio. O valor original nunca é alterado; o normalizado
vai para uma coluna nova (`cid_norm`, `nome_norm`, `municipio_norm`, `prioridade_norm`).
"""
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

PRE_CID = "PRE-01"
PRE_NOME = "PRE-02"
PRE_MUNICIPIO = "PRE-03"
PRE_PRIORIDADE = "PRE-04"

PRIORIDADES = {"alta", "media", "baixa"}

def _chave(texto: str) -> str:
    """Minúsculo, sem acento e com espaços colapsados."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


# Chave de busca (sem acento, minúsculo) -> nome oficial do IBGE.
# Cobre os 38 municípios do dataset; um teste garante que nenhum valor do CSV fica de fora.
MUNICIPIOS_OFICIAIS: Dict[str, str] = {
    _chave(nome): nome
    for nome in [
        "Alegrete", "Alvorada", "Bagé", "Cachoeira do Sul", "Cachoeirinha", "Camaquã",
        "Canoas", "Caxias do Sul", "Charqueadas", "Cruz Alta", "Eldorado do Sul", "Erechim",
        "Esteio", "Gravataí", "Guaíba", "Ijuí", "Lajeado", "Montenegro", "Novo Hamburgo",
        "Osório", "Passo Fundo", "Pelotas", "Porto Alegre", "Rio Grande", "Santa Cruz do Sul",
        "Santa Maria", "Santa Rosa", "Santana do Livramento", "Santo Ângelo", "São Borja",
        "São Gabriel", "São Leopoldo", "Sapucaia do Sul", "Taquara", "Torres", "Tramandaí",
        "Uruguaiana", "Viamão",
    ]
}


@dataclass(frozen=True)
class Correcao:
    campo: str
    original: Optional[str]
    novo: Optional[str]
    regra: str


def normalize_cid(raw: Optional[str]) -> Optional[str]:
    """PRE-01: maiúsculo e sem ponto (`K42.9` e `K429` -> `K429`)."""
    if raw is None or not raw.strip():
        return None
    return raw.strip().upper().replace(".", "")


def normalize_nome(raw: Optional[str]) -> Optional[str]:
    """PRE-02: chave de comparação sem caixa, acento e espaço repetido."""
    if raw is None or not raw.strip():
        return None
    return _chave(raw)


def normalize_municipio(raw: Optional[str]) -> Optional[str]:
    """PRE-03: nome oficial do IBGE. Município fora da tabela volta só sem espaços sobrando."""
    if raw is None or not raw.strip():
        return None
    return MUNICIPIOS_OFICIAIS.get(_chave(raw), " ".join(raw.split()))


def normalize_prioridade(raw: Optional[str]) -> Optional[str]:
    """PRE-04: `alta`/`media`/`baixa`, ou vazio (inclusive para valor desconhecido)."""
    if raw is None or not raw.strip():
        return None
    chave = _chave(raw)
    return chave if chave in PRIORIDADES else None


def preprocess_solicitacao(
    row: Mapping[str, Optional[str]],
) -> Tuple[Dict[str, Optional[str]], List[Correcao]]:
    """Devolve as colunas normalizadas e as correções a registrar em `correcoes_log`.

    Entram no log as mudanças de valor visíveis: município e prioridade que mudam de
    grafia, e CID com defeito além do ponto (minúsculo ou espaço). `cid_norm` sem ponto e
    `nome_norm` são chaves de comparação (D-17): a diferença é esperada e não vira log.
    """
    cid, nome = row.get("cid_principal"), row.get("nome_paciente")
    municipio, prioridade = row.get("municipio"), row.get("prioridade_regulacao")

    norm = {
        "cid_norm": normalize_cid(cid),
        "nome_norm": normalize_nome(nome),
        "municipio_norm": normalize_municipio(municipio),
        "prioridade_norm": normalize_prioridade(prioridade),
    }

    correcoes: List[Correcao] = []
    if cid and cid != cid.strip().upper():
        correcoes.append(Correcao("cid_principal", cid, norm["cid_norm"], PRE_CID))
    if municipio and municipio.strip() and municipio != norm["municipio_norm"]:
        correcoes.append(Correcao("municipio", municipio, norm["municipio_norm"], PRE_MUNICIPIO))
    if prioridade and prioridade.strip() and prioridade != norm["prioridade_norm"]:
        correcoes.append(
            Correcao("prioridade_regulacao", prioridade, norm["prioridade_norm"], PRE_PRIORIDADE)
        )
    return norm, correcoes
