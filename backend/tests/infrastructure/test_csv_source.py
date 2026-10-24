from __future__ import annotations

import pytest

from app.config import settings
from app.infrastructure.csv_source import carregar_do_csv

pytestmark = pytest.mark.skipif(
    not (settings.data_dir / "fila_cirurgica.csv").exists(), reason="dataset ausente")


@pytest.fixture(scope="module")
def dados():
    return carregar_do_csv(settings.data_dir)


def test_total_de_solicitacoes(dados):
    assert len(dados[0]) == 941


def test_oncologico_usa_cid_e_nao_a_flag(dados):
    s = {x.solicitacao_id: x for x in dados[0]}
    assert s["SOL-2025-00149"].cid_principal.startswith("C61")
    assert s["SOL-2025-00149"].flag_oncologico == "nao" and s["SOL-2025-00149"].oncologico
    assert s["SOL-2026-00583"].flag_oncologico == "sim" and not s["SOL-2026-00583"].oncologico
    assert sum(x.oncologico for x in dados[0]) == 177


def test_duplicados_marcados(dados):
    ev = {e.evento_id: e for e in dados[1]["SOL-2023-00083"]}
    assert ev["EVT-000050"].duplicado_de is None
    assert ev["EVT-000051"].duplicado_de == "EVT-000050"


def test_historico_pronto_socorro(dados):
    ps = [e for e in dados[1]["SOL-2023-00017"] if e.tipo_evento == "pronto_socorro"]
    assert ps and all(e.historico for e in ps)


def test_orfaos_fora_do_dict(dados):
    ids = {s.solicitacao_id for s in dados[0]}
    assert set(dados[1]) <= ids
