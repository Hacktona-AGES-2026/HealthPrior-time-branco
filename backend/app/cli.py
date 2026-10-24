"""Comandos de linha (rode dentro de backend/):

    python -m app.cli init-db     cria as tabelas
    python -m app.cli carga       US-01: carga inicial
    python -m app.cli gerar-fila  US-08/09/10: gera, verifica e publica fila_priorizada.csv
    python -m app.cli decisoes    US-11: lista exclusões para o DECISOES.md
"""
import argparse
import sys

from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import criar_tabelas, engine
from app.infrastructure.repositories import SqlCargaRepository


def cmd_init_db() -> None:
    criar_tabelas()
    print(f"Tabelas criadas em {settings.db_url}")


def cmd_carga() -> None:
    criar_tabelas()
    with Session(engine) as session:
        try:
            resumo = CargaInicial(LeitorDataset(), SqlCargaRepository(session)).executar()
        except CargaInvalidaError as e:
            sys.exit(f"Erro na carga: {e.mensagem}")
    for tabela, r in vars(resumo).items():
        print(f"{tabela}: {r.lido} lidos, {r.inseridos} inseridos, {r.atualizados} atualizados")


def cmd_gerar_fila() -> None:
    raise NotImplementedError("US-08/09/10: montar GerarFila (ver app/api/deps.py) e executar")


def cmd_decisoes() -> None:
    raise NotImplementedError("US-11: gerar tabela de exclusões")


COMANDOS = {"init-db": cmd_init_db, "carga": cmd_carga, "gerar-fila": cmd_gerar_fila,
            "decisoes": cmd_decisoes}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("comando", choices=COMANDOS)
    COMANDOS[parser.parse_args().comando]()


if __name__ == "__main__":
    main()
