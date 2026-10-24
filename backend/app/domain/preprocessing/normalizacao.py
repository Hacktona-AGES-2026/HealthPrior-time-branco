"""PRE-01..PRE-04 (US-02). Funções puras sobre valores escalares."""
from __future__ import annotations

import unicodedata

from dataclasses import replace

from app.domain.cid import normalizar_cid
from app.domain.models import Correcao, Solicitacao

PRE_CID = "PRE-01"
PRE_NOME = "PRE-02"
PRE_MUNICIPIO = "PRE-03"
PRE_PRIORIDADE = "PRE-04"
REGRAS_NORMALIZACAO = (PRE_CID, PRE_NOME, PRE_MUNICIPIO, PRE_PRIORIDADE)

PRIORIDADES = frozenset({"alta", "media", "baixa"})


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
    """PRE-04: 'Média' -> 'media'. Vazio ou desconhecido (ex.: 'urgente') -> None (D-21)."""
    if not prioridade or not prioridade.strip():
        return None
    chave = remover_acentos(prioridade).strip().lower()
    return chave if chave in PRIORIDADES else None


def normalizar_municipio(municipio: str | None, oficiais: dict[str, str]) -> str | None:
    """PRE-03: mapeia para o nome oficial.

    `oficiais` é {chave_normalizada: nome_oficial}, montado pela infraestrutura (IBGE ou dataset).
    Município fora da tabela volta só sem espaços sobrando.
    """
    if not municipio or not municipio.strip():
        return None
    return oficiais.get(normalizar_nome(municipio), " ".join(municipio.split()))


def normalizar_solicitacao(
    s: Solicitacao, municipios_oficiais: dict[str, str]
) -> tuple[Solicitacao, list[Correcao]]:
    """PRE-01..04: devolve a solicitação com as colunas *_norm e as correções a registrar.

    O valor original nunca muda. Entram no log só mudanças de valor visíveis: município e
    prioridade que mudam de grafia, e CID com defeito além do ponto (minúsculo ou espaço).
    `cid_norm` sem ponto e `nome_norm` são chaves de comparação (D-18): a diferença é esperada
    e não vira log.
    """
    cid_norm = normalizar_cid(s.cid_principal)
    municipio_norm = normalizar_municipio(s.municipio, municipios_oficiais)
    prioridade_norm = normalizar_prioridade(s.prioridade_regulacao)
    normalizada = replace(
        s,
        cid_norm=cid_norm,
        nome_norm=normalizar_nome(s.nome_paciente),
        municipio_norm=municipio_norm,
        prioridade_norm=prioridade_norm,
    )

    correcoes: list[Correcao] = []
    cid = s.cid_principal
    if cid and cid != cid.strip().upper():
        correcoes.append(Correcao(s.solicitacao_id, "cid_principal", cid, cid_norm, PRE_CID))
    if s.municipio and s.municipio.strip() and s.municipio != municipio_norm:
        correcoes.append(Correcao(s.solicitacao_id, "municipio", s.municipio, municipio_norm, PRE_MUNICIPIO))
    if s.prioridade_regulacao and s.prioridade_regulacao.strip() and s.prioridade_regulacao != prioridade_norm:
        correcoes.append(Correcao(s.solicitacao_id, "prioridade_regulacao", s.prioridade_regulacao,
                                  prioridade_norm, PRE_PRIORIDADE))
    return normalizada, correcoes
