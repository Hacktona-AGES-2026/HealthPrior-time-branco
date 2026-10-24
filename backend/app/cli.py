"""Comandos de linha (rode dentro de backend/):

    python -m app.cli init-db     cria as tabelas
    python -m app.cli carga       US-01: carga inicial (+ pré-processamento)
    python -m app.cli preprocessar  US-03: recalcula flags e marca eventos (sem recarregar)
    python -m app.cli gerar-fila  US-08/09/10: gera, verifica e publica fila_priorizada.csv
    python -m app.cli decisoes    US-11: lista exclusões para o DECISOES.md
"""
import argparse
import sys

from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.preprocessar import Preprocessar, ResumoPreprocessamento
from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import criar_tabelas, engine
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)


def _preprocessar(session: Session) -> Preprocessar:
    return Preprocessar(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                        SqlCorrecaoRepository(session), SqlUnidadeDeTrabalho(session))


def _imprimir_preprocessamento(r: ResumoPreprocessamento) -> None:
    por_regra = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.correcoes.items())) or "nenhuma"
    print(f"pré-processamento: {r.solicitacoes} solicitações, correções ({por_regra})")
    print(f"eventos: {r.eventos_duplicados} duplicados, {r.eventos_historicos} históricos")


def cmd_init_db() -> None:
    criar_tabelas()
    print(f"Tabelas criadas em {settings.db_url}")


def cmd_carga() -> None:
    criar_tabelas()
    with Session(engine) as session:
        try:
            resumo = CargaInicial(LeitorDataset(), SqlCargaRepository(session),
                                  _preprocessar(session)).executar()
        except CargaInvalidaError as e:
            sys.exit(f"Erro na carga: {e.mensagem}")
    for tabela in ("procedimentos", "solicitacoes", "eventos"):
        r = getattr(resumo, tabela)
        print(f"{tabela}: {r.lido} lidos, {r.inseridos} inseridos, {r.atualizados} atualizados")
    _imprimir_preprocessamento(resumo.preprocessamento)


def cmd_preprocessar() -> None:
    criar_tabelas()
    with Session(engine) as session:
        _imprimir_preprocessamento(_preprocessar(session).executar())


def cmd_gerar_fila() -> None:
    raise NotImplementedError("US-08/09/10: montar GerarFila (ver app/api/deps.py) e executar")


def cmd_decisoes() -> None:
    raise NotImplementedError("US-11: gerar tabela de exclusões")


COMANDOS = {"init-db": cmd_init_db, "carga": cmd_carga, "preprocessar": cmd_preprocessar,
            "gerar-fila": cmd_gerar_fila, "decisoes": cmd_decisoes}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("comando", choices=COMANDOS)
    COMANDOS[parser.parse_args().comando]()


if __name__ == "__main__":
    main()
