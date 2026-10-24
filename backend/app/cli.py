"""Comandos de linha (rode dentro de backend/):

    python -m app.cli init-db     cria as tabelas
    python -m app.cli carga       US-01/02: carga inicial + normalização (mesma transação)
    python -m app.cli normalizar  US-02: recalcula as colunas *_norm e o correcoes_log
    python -m app.cli gerar-fila  US-08/09/10: gera, verifica e publica fila_priorizada.csv
    python -m app.cli decisoes    US-11: lista exclusões para o DECISOES.md
"""
import argparse
import sys

from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.normalizar import Normalizar, ResumoNormalizacao
from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import criar_tabelas, engine
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)


def cmd_init_db() -> None:
    criar_tabelas()
    print(f"Tabelas criadas em {settings.db_url}")


def _imprimir_normalizacao(r: ResumoNormalizacao) -> None:
    regras = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.por_regra.items())) or "nenhuma"
    print(f"normalização: {r.solicitacoes} solicitações, {r.correcoes} correções ({regras})")


def cmd_carga() -> None:
    criar_tabelas()
    with Session(engine) as session:
        normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
        try:
            resumo = CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                                  SqlUnidadeDeTrabalho(session)).executar()
        except CargaInvalidaError as e:
            sys.exit(f"Erro na carga: {e.mensagem}")
    for tabela in ("procedimentos", "solicitacoes", "eventos"):
        r = getattr(resumo, tabela)
        print(f"{tabela}: {r.lido} lidos, {r.inseridos} inseridos, {r.atualizados} atualizados")
    _imprimir_normalizacao(resumo.normalizacao)


def cmd_normalizar() -> None:
    with Session(engine) as session:
        resumo = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session)).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    _imprimir_normalizacao(resumo)


def cmd_gerar_fila() -> None:
    raise NotImplementedError("US-08/09/10: montar GerarFila (ver app/api/deps.py) e executar")


def cmd_decisoes() -> None:
    raise NotImplementedError("US-11: gerar tabela de exclusões")


COMANDOS = {"init-db": cmd_init_db, "carga": cmd_carga, "normalizar": cmd_normalizar,
            "gerar-fila": cmd_gerar_fila, "decisoes": cmd_decisoes}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("comando", choices=COMANDOS)
    COMANDOS[parser.parse_args().comando]()


if __name__ == "__main__":
    main()
