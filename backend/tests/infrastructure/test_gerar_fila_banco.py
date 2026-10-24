"""US-09 · fila gerada a partir do banco com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import csv
import subprocess
import sys

from app.application.gerar_fila import GerarFila
from app.application.normalizar import Normalizar
from app.application.carga_inicial import CargaInicial
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_stub import SwalisStub


def test_gera_fila_do_banco_e_passa_no_verificador(session, tmp_path):
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                 SqlUnidadeDeTrabalho(session)).executar()

    destino = tmp_path / "fila_priorizada.csv"
    r = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                  SwalisStub(), ExportadorCsv(), settings.ref_date).executar(destino)

    assert r.total == 941
    assert r.por_camada[1] == 177
    assert [l.posicao for l in r.linhas] == list(range(1, 942))
    assert r.linhas[0].solicitacao_id == "SOL-2023-00010"
    with destino.open(encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 941

    proc = subprocess.run(
        [sys.executable, str(settings.verificador_path), str(destino),
         "--dataset", str(settings.data_dir)],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
