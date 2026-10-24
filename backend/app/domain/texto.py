"""Busca de termos no texto clínico com tratamento de negação (SW-04).

"Sem sinais de encarceramento" não pode virar urgência. Um termo precedido de negação
("sem", "nega", "nunca", "ausência de", "não há", "descarta") na mesma oração é ignorado.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

NEGACOES = re.compile(r"\b(?:sem|nega|negou|negam|nunca|ausencia de|nao ha|nao houve|descarta|descartad[oa])\b")
# Fim do escopo da negação: fim de frase, pontuação de oração ou conjunção adversativa.
# "Sem melhora, evoluiu com suboclusão" -> a suboclusão NÃO fica negada.
_FIM_DE_ESCOPO = re.compile(r"[.;:!?,\n|]|\b(?:mas|porem|entretanto|contudo|evoluiu|evoluindo)\b")


def normalizar_texto(texto: str | None) -> str:
    """Minúsculo e sem acento. Mantém o comprimento (posições batem com o original)."""
    if not texto:
        return ""
    sem_acento = (unicodedata.normalize("NFD", c)[0] for c in texto.lower())
    return "".join(sem_acento)


@dataclass(frozen=True)
class Ocorrencia:
    termo: str
    trecho: str  # oração do texto original onde o termo aparece (evidência citável)
    negado: bool


def _inicio_da_oracao(texto_norm: str, pos: int) -> int:
    inicio = 0
    for m in _FIM_DE_ESCOPO.finditer(texto_norm, 0, pos):
        inicio = m.end()
    return inicio


def _fim_da_oracao(texto_norm: str, pos: int) -> int:
    m = re.compile(r"[.;!?\n|]").search(texto_norm, pos)
    return m.start() if m else len(texto_norm)


def esta_negado(texto: str, inicio_termo: int) -> bool:
    """True se há negação antes do termo, dentro da mesma oração."""
    texto_norm = normalizar_texto(texto)
    escopo = texto_norm[_inicio_da_oracao(texto_norm, inicio_termo):inicio_termo]
    return bool(NEGACOES.search(escopo))


def buscar_termos(texto: str | None, padrao: re.Pattern[str]) -> list[Ocorrencia]:
    """Todas as ocorrências de `padrao` (escrito sem acento, minúsculo) no texto."""
    if not texto:
        return []
    texto_norm = normalizar_texto(texto)
    ocorrencias = []
    for m in padrao.finditer(texto_norm):
        ini = texto_norm.rfind(".", 0, m.start()) + 1
        trecho = texto[ini:_fim_da_oracao(texto_norm, m.end())].strip()
        ocorrencias.append(Ocorrencia(m.group(0), trecho, esta_negado(texto, m.start())))
    return ocorrencias


def frases(texto: str | None) -> list[str]:
    """Frases do texto original (cortadas em . ; ! ? e quebra de linha), sem as vazias."""
    return [f.strip() for f in re.split(r"[.;!?\n]", texto or "") if f.strip()]


def localizar_trecho(texto: str | None, trecho: str) -> tuple[int, int] | None:
    """(início, fim) de `trecho` no texto, ignorando caixa, acento e espaços repetidos."""
    palavras = normalizar_texto(trecho).split()
    if not texto or not palavras:
        return None
    m = re.search(r"\s+".join(map(re.escape, palavras)), normalizar_texto(texto))
    return m.span() if m else None
