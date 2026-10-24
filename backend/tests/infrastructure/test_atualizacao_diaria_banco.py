"""US-16 · atualização diária com o dataset real (precisa do Postgres de teste).

Compõe como o `api/deps.py`: a mesma data vai para o GerarFila e para o SWALIS.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.api.deps import get_data_referencia, get_detalhar_solicitacao
from app.application.atualizacao_diaria import AtualizacaoDiaria
from app.application.carga_inicial import CargaInicial
from app.application.gerar_fila import GerarFila
from app.application.normalizar import Normalizar
from app.application.publicar_fila import PublicarFila
from app.application.recalcular_flags import RecalcularFlags
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.tables import SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial

REF = settings.ref_date
EDITADO = "SOL-2026-00757"


def carregar(session):
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    flags = RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                            SqlCorrecaoRepository(session))
    return CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session), flags).executar()


@pytest.fixture
def carregado(_dataset_carregado):
    return _dataset_carregado[1]


def _atualizacao(session, tmp_path) -> AtualizacaoDiaria:
    def publicar_em(data: date) -> PublicarFila:
        gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                          criar_swalis(ref_date=data), ExportadorCsv(), data)
        return PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session),
                            SqlUnidadeDeTrabalho(session),
                            lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path)

    return AtualizacaoDiaria(SqlFilaRepository(session), publicar_em, REF)


def _publicada(session) -> dict:
    return {l.solicitacao_id: l for l in SqlFilaRepository(session).obter_publicada()}


def test_avancar_um_dia_envelhece_todos_e_passa_no_verificador(session, carregado, tmp_path):
    # edição do regulador (US-14) direto na tabela: o score editado também envelhece (C-10)
    session.execute(update(SolicitacaoTable).where(SolicitacaoTable.solicitacao_id == EDITADO)
                    .values(classe_medico="D", editado_manualmente=True))
    atualizar = _atualizacao(session, tmp_path)

    r0 = atualizar.executar(REF)
    assert r0.publicada and r0.data_referencia == REF
    antes = _publicada(session)

    r1 = atualizar.executar()  # sem data: +1 dia a partir da última publicada
    assert r1.publicada, r1.saida_verificador
    assert "RESULTADO: OK" in r1.saida_verificador
    assert r1.data_referencia == REF + timedelta(days=1)
    assert SqlFilaRepository(session).data_referencia() == REF + timedelta(days=1)

    depois = _publicada(session)
    assert depois.keys() == antes.keys() and len(depois) == 941
    for sid, linha in depois.items():
        assert linha.dias_em_fila == antes[sid].dias_em_fila + 1, sid
        # pacientes com e sem classe editada: o SWALIS também recebeu a data nova
        assert linha.pct_prazo_consumido > antes[sid].pct_prazo_consumido, sid
    assert depois[EDITADO].editado_manualmente and depois[EDITADO].classe == "D"

    # Detalhe (GET /solicitacoes/{id}) com a composição real: mesma data da fila publicada.
    detalhar = get_detalhar_solicitacao(session, get_data_referencia(session))
    for sid in (EDITADO, "SOL-2023-00010", "SOL-2025-00149"):
        d = detalhar.executar(sid)
        assert d.score.pct_prazo_consumido == depois[sid].pct_prazo_consumido, sid
        assert f"{depois[sid].dias_em_fila} dias" in d.explicacao, sid


def test_mesma_data_duas_vezes_da_a_mesma_fila(session, carregado, tmp_path):
    atualizar = _atualizacao(session, tmp_path)
    data = date(2026, 10, 30)

    r1 = atualizar.executar(data)
    primeira = SqlFilaRepository(session).obter_publicada()
    csv1 = r1.caminho_csv.read_text(encoding="utf-8")
    r2 = atualizar.executar(data)

    assert r1.publicada and r2.publicada
    assert SqlFilaRepository(session).obter_publicada() == primeira
    assert r2.caminho_csv.read_text(encoding="utf-8") == csv1
    assert SqlFilaRepository(session).data_referencia() == data
    entrada = SqlSolicitacaoRepository(session).obter(primeira[0].solicitacao_id).data_entrada_fila
    assert primeira[0].dias_em_fila == (data - entrada).days
