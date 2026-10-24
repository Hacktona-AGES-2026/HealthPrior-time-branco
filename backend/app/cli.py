import argparse
import sys
from pathlib import Path

from app import config
from app.db import get_engine
from app.loader import CargaError, carga
from app.normalization import NormalizacaoResult, normalizar


def cmd_carga(args: argparse.Namespace) -> int:
    try:
        resultado = carga(get_engine(), Path(args.data_dir))
    except CargaError as e:
        print(f"Erro na carga: {e}", file=sys.stderr)
        return 1
    for tabela, r in resultado.tabelas.items():
        print(f"{tabela}: {r.lido} lidos, {r.inseridos} inseridos, {r.atualizados} atualizados")
    _print_normalizacao(resultado.normalizacao)
    return 0


def cmd_normalizar(_: argparse.Namespace) -> int:
    with get_engine().begin() as conn:
        _print_normalizacao(normalizar(conn))
    return 0


def _print_normalizacao(r: NormalizacaoResult) -> None:
    regras = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.por_regra.items())) or "nenhuma"
    print(f"normalização: {r.solicitacoes} solicitações, {r.correcoes} correções ({regras})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("carga", help="carrega os CSVs de data/ no banco (idempotente)")
    p.add_argument("--data-dir", default=str(config.DATA_DIR))
    p.set_defaults(func=cmd_carga)

    p = sub.add_parser("normalizar", help="recalcula as colunas normalizadas e o correcoes_log")
    p.set_defaults(func=cmd_normalizar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
