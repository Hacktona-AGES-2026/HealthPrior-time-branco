"""Guarda da regra de dependência da Clean Architecture.

domain      -> não importa application, infrastructure, api, fastapi, sqlmodel, pandas
application -> não importa infrastructure, api, fastapi, sqlmodel
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

PROIBIDOS = {
    "domain": ("app.application", "app.infrastructure", "app.api", "fastapi", "sqlmodel", "pandas"),
    "application": ("app.infrastructure", "app.api", "fastapi", "sqlmodel"),
}


def _imports(arquivo: Path) -> set[str]:
    nomes = set()
    for node in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            nomes.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            nomes.add(node.module)
    return nomes


def test_regra_de_dependencia():
    violacoes = []
    for camada, proibidos in PROIBIDOS.items():
        for arquivo in (APP / camada).rglob("*.py"):
            for imp in _imports(arquivo):
                if imp.startswith(proibidos):
                    violacoes.append(f"{arquivo.relative_to(APP)} importa {imp}")
    assert not violacoes, "\n".join(violacoes)
