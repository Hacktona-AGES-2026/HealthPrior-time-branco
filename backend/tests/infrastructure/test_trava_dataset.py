"""C-11 · D-112: quem divide o bloco prioritário com os oncológicos é urgente para o verificador.

Com as camadas 1 e 2 num bloco só, um urgente pode passar um oncológico. Isso só respeita a
regra de ouro (I-01) se nenhum paciente da camada 2 for "sem urgência" pela definição do
verificador oficial. A definição aqui sai do próprio `src/verificar_fila_priorizada.py`
(constantes importadas e a lista de eventos copiada de lá), e não de `domain/urgencia.py`:
assim, um sinal novo só do nosso lado quebra este teste em vez de só travar a publicação.
"""
from __future__ import annotations

import csv
import importlib.util
import re

import pytest

from app.application.montar_fila import montar_fila
from app.config import settings
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.swalis_regras import criar_swalis

VERIFICADOR = settings.data_dir.parent / "src" / "verificar_fila_priorizada.py"

pytestmark = pytest.mark.skipif(
    not ((settings.data_dir / "fila_cirurgica.csv").exists() and VERIFICADOR.exists()),
    reason="dataset ou verificador ausente")

# Copiado de `piora_ids` em src/verificar_fila_priorizada.py (fica dentro do main(), sem import).
EVENTOS_DE_PIORA_VERIFICADOR = {("pronto_socorro", None), ("internacao", None),
                                ("biopsia", "positivo"), ("exame_imagem", "progressao"),
                                ("consulta_reavaliacao", "piora")}


def _verificador():
    spec = importlib.util.spec_from_file_location("verificador_oficial", VERIFICADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _sem_urgencia_pelo_verificador() -> tuple[set[str], set[str]]:
    """(oncológicos, sem urgência) com a fórmula e o CSV cru, como o verificador lê."""
    v = _verificador()
    with (settings.data_dir / "eventos_clinicos.csv").open(newline="") as f:
        piora = {e["solicitacao_id"] for e in csv.DictReader(f)
                 if (e["tipo_evento"], None) in EVENTOS_DE_PIORA_VERIFICADOR
                 or (e["tipo_evento"], e["resultado"]) in EVENTOS_DE_PIORA_VERIFICADOR}
    alarme = re.compile(v.KW_ALARME)
    onco, calmos = set(), set()
    with (settings.data_dir / "fila_cirurgica.csv").open(newline="") as f:
        for s in csv.DictReader(f):
            cid = s["cid_principal"].upper().replace(".", "")
            if cid.startswith("C"):
                onco.add(s["solicitacao_id"])
                continue
            dor = float(s["intensidade_dor_eva"] or 0)
            limitacao = s["limitacao_funcional"] or "nenhuma"
            if (dor <= 3 and limitacao in ("nenhuma", "leve") and cid not in v.CID_URGENTE
                    and s["solicitacao_id"] not in piora
                    and not alarme.search(s["justificativa_clinica"].lower())):
                calmos.add(s["solicitacao_id"])
    return onco, calmos


@pytest.fixture(scope="module")
def fila():
    solicitacoes, eventos = carregar_do_csv(settings.data_dir)
    return montar_fila(solicitacoes, eventos, criar_swalis(), settings.ref_date)


def test_nenhum_paciente_da_camada_2_e_sem_urgencia_para_o_verificador(fila):
    _, calmos = _sem_urgencia_pelo_verificador()
    camada_2 = {l.solicitacao_id for l in fila if l.camada == 2}

    assert camada_2, "a camada 2 não deveria estar vazia no dataset"
    assert camada_2 & calmos == set()


def test_camada_1_sao_exatamente_os_oncologicos_do_verificador(fila):
    onco, _ = _sem_urgencia_pelo_verificador()

    assert {l.solicitacao_id for l in fila if l.camada == 1} == onco
