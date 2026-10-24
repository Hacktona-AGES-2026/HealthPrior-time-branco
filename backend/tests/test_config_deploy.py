"""Configuração de deploy: URL do banco (Render/Neon) e origens do CORS."""
import importlib

import pytest

from app import config


def recarregar(monkeypatch, **env):
    for k in ("HP_DB_URL", "DATABASE_URL", "HP_CORS_ORIGINS"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return config._url_do_banco(), config._origens_cors()


@pytest.mark.parametrize("entrada,esperada", [
    ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
])
def test_url_do_banco_vira_psycopg3(monkeypatch, entrada, esperada):
    assert recarregar(monkeypatch, DATABASE_URL=entrada)[0] == esperada


def test_hp_db_url_vence_database_url_e_o_padrao_e_o_compose(monkeypatch):
    assert recarregar(monkeypatch, HP_DB_URL="postgresql+psycopg://a/b", DATABASE_URL="postgres://c/d")[0] == "postgresql+psycopg://a/b"
    assert "localhost:5432/healthprior" in recarregar(monkeypatch)[0]


def test_cors_soma_as_origens_do_ambiente_sem_barra_final(monkeypatch):
    local = ("http://localhost:5173", "http://127.0.0.1:5173")
    assert recarregar(monkeypatch)[1] == local
    assert recarregar(monkeypatch, HP_CORS_ORIGINS="https://app.vercel.app/, https://x.com")[1] == local + ("https://app.vercel.app", "https://x.com")


def test_imagem_docker_leva_a_tabela_de_irr_dos_fatores_do_score():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    assert (raiz / "score" / "references" / "irr_nacional_cid_idade_2019_2023.csv").is_file()
    assert "COPY score/references score/references" in (raiz / "backend" / "Dockerfile").read_text()
    linhas = (raiz / ".dockerignore").read_text().split()
    assert "score" not in linhas and "!score/references" in linhas
