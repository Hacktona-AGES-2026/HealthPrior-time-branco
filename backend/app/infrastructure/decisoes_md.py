"""Grava a tabela de exclusões na seção "Solicitações fora da fila" do DECISOES.md (US-11)."""
from __future__ import annotations

from pathlib import Path

from app.domain.exclusoes import substituir_secao


def gravar_secao(caminho: Path, conteudo: str) -> None:
    caminho.write_text(substituir_secao(caminho.read_text(encoding="utf-8"), conteudo), encoding="utf-8")
