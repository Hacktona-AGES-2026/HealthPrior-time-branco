"""US-22 · Confere os indicadores 'antes' contra o verificador oficial, sem banco."""
from __future__ import annotations

import csv
import re
import subprocess
import sys

import pytest

from app.config import settings
from app.domain.metricas import (
    calcular_indicadores,
    com_ps_recente,
    is_sem_urgencia_verificador,
    ordem_atual,
)
from app.infrastructure.csv_source import carregar_do_csv

REPO = settings.data_dir.parent
VERIFICADOR = REPO / "src" / "verificar_fila_priorizada.py"

pytestmark = pytest.mark.skipif(
    not ((settings.data_dir / "fila_cirurgica.csv").exists() and VERIFICADOR.exists()),
    reason="dataset ou verificador ausente")


def test_antes_bate_com_o_verificador(tmp_path, capsys):
    sols, eventos = carregar_do_csv(settings.data_dir)
    ordem = ordem_atual(sols)
    onco = {s.solicitacao_id for s in sols if s.oncologico}
    calmos = {s.solicitacao_id for s in sols
              if is_sem_urgencia_verificador(s, eventos.get(s.solicitacao_id, []))}
    ind = calcular_indicadores(ordem, onco, calmos, com_ps_recente(eventos, settings.ref_date))

    arq = tmp_path / "antes.csv"
    with arq.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["solicitacao_id", "posicao", "justificativa"])
        for i, sid in enumerate(ordem, start=1):
            w.writerow([sid, i, "x"])
    r = subprocess.run([sys.executable, str(VERIFICADOR), str(arq), "--dataset",
                        str(settings.data_dir)], capture_output=True, text=True)
    saida = r.stdout
    print("\nANTES (nosso):", ind)
    print(saida)

    m = re.search(r"REGRA DE OURO VIOLADA: (\d+)", saida)
    assert ind.violacoes_regra_ouro == (int(m.group(1)) if m else 0)
    med = float(re.search(r"mediana dos oncol\S+: (\d+) de", saida).group(1))
    assert abs(ind.posicao_mediana_oncologicos - med) <= 0.5
    for rotulo, valor in (
            (r"oncológicos no primeiro terço", ind.pct_oncologicos_primeiro_terco),
            (r"na primeira metade", ind.pct_ps_recente_primeira_metade),
            (r"no último terço", ind.pct_sem_urgencia_ultimo_terco)):
        p = float(re.search(rotulo + r": (\d+)%", saida).group(1))
        assert abs(valor - p) <= 0.5
