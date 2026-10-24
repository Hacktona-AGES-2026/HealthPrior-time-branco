"""PRE-01..PRE-04 (US-02). Funções puras sobre valores escalares."""
from __future__ import annotations

import unicodedata

from app.domain.cid import normalizar_cid  # noqa: F401  (PRE-01 reexportado)


def remover_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def normalizar_nome(nome: str | None) -> str:
    """PRE-02: chave de comparação. 'JUREMA Quadros  Weber' -> 'jurema quadros weber'."""
    if not nome:
        return ""
    return " ".join(remover_acentos(nome).lower().split())


def normalizar_prioridade(prioridade: str | None) -> str | None:
    """PRE-04: 'Média' -> 'media'; vazio -> None."""
    if not prioridade or not prioridade.strip():
        return None
    return remover_acentos(prioridade).strip().lower()


def normalizar_municipio(municipio: str | None, oficiais: dict[str, str]) -> str | None:
    """PRE-03: mapeia para o nome oficial.

    `oficiais` é {chave_normalizada: nome_oficial}, montado pela infraestrutura (IBGE ou dataset).
    TODO(US-02): montar o dicionário de municípios oficiais.
    """
    if not municipio:
        return None
    return oficiais.get(normalizar_nome(municipio), municipio.strip())
