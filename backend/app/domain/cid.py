"""Regras sobre CID-10 (PRE-01, PRE-05, I-09)."""
from __future__ import annotations

# CIDs de complicação/instabilidade (mesma lista do verificador oficial).
CID_URGENTE: frozenset[str] = frozenset(
    {"I200", "K403", "K400", "K420", "K430", "K800", "N132", "I832"}
)


def normalizar_cid(cid: str | None) -> str:
    """'k40.9 ' -> 'K409'. Vazio vira ''."""
    if not cid:
        return ""
    return cid.strip().upper().replace(".", "")


def is_oncologico(cid: str | None) -> bool:
    """Neoplasia maligna: CID normalizado começa com 'C'. Use sempre isto, nunca a flag (I-09)."""
    return normalizar_cid(cid).startswith("C")


def is_lesao_incerta(cid: str | None) -> bool:
    """D37–D48 (comportamento incerto) e R91 (achado suspeito)."""
    c = normalizar_cid(cid)
    if c.startswith("R91"):
        return True
    return c[:1] == "D" and c[1:3].isdigit() and 37 <= int(c[1:3]) <= 48


def is_cid_urgente(cid: str | None) -> bool:
    return normalizar_cid(cid) in CID_URGENTE
