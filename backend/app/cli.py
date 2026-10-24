"""Comandos de linha (rode dentro de backend/):

    python -m app.cli init-db     cria as tabelas
    python -m app.cli carga       US-01: carga inicial
    python -m app.cli gerar-fila  US-08/09/10: gera, verifica e publica fila_priorizada.csv (via banco)
    python -m app.cli gerar-fila-csv  US-08 provisório (D-19): gera a fila direto do dataset, sem banco
    python -m app.cli decisoes    US-11: lista exclusões para o DECISOES.md
"""
import argparse
import sys
from collections import Counter

from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.montar_fila import linhas_para_dicts, montar_fila
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.swalis_stub import SwalisStub
from app.infrastructure.verificador import VerificadorOficial
from app.infrastructure.db import criar_tabelas, engine
from app.infrastructure.repositories import SqlEventoRepository, SqlSolicitacaoRepository


def cmd_init_db() -> None:
    criar_tabelas()
    print(f"Tabelas criadas em {settings.db_url}")


def cmd_carga() -> None:
    criar_tabelas()
    with Session(engine) as session:
        resumo = CargaInicial(LeitorDataset(), SqlSolicitacaoRepository(session),
                              SqlEventoRepository(session)).executar()
    print(resumo)


def cmd_gerar_fila() -> None:
    raise NotImplementedError("US-08/09/10: montar GerarFila (ver app/api/deps.py) e executar")


def cmd_gerar_fila_csv() -> None:
    """Gera output/fila_priorizada.csv direto do dataset (sem banco) e roda o verificador (I-07).

    Provisório (D-19): substituído por `gerar-fila` quando a US-01 (carga no banco) existir.
    """
    solicitacoes, eventos = carregar_do_csv(settings.data_dir)
    linhas = montar_fila(solicitacoes, eventos, SwalisStub(), settings.ref_date)
    csv_path = ExportadorCsv().exportar(linhas_para_dicts(linhas),
                                        settings.output_dir / "fila_priorizada.csv")
    passou, saida = VerificadorOficial().verificar(csv_path)
    print(saida, end="")
    por_camada = Counter(linha.camada for linha in linhas)
    print(f"Arquivo: {csv_path}")
    print(f"Total: {len(linhas)} | " + " | ".join(
        f"camada {c}: {por_camada.get(c, 0)}" for c in (1, 2, 3)))
    if not passou:
        print("FILA NÃO PUBLICADA: o verificador falhou (I-07).", file=sys.stderr)
        sys.exit(1)


def cmd_decisoes() -> None:
    raise NotImplementedError("US-11: gerar tabela de exclusões")


COMANDOS = {"init-db": cmd_init_db, "carga": cmd_carga, "gerar-fila": cmd_gerar_fila,
            "gerar-fila-csv": cmd_gerar_fila_csv, "decisoes": cmd_decisoes}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("comando", choices=COMANDOS)
    COMANDOS[parser.parse_args().comando]()


if __name__ == "__main__":
    main()
