"""US-10 · publicação no banco com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.application.carga_inicial import CargaInicial
from app.application.gerar_fila import GerarFila
from app.application.normalizar import Normalizar
from app.application.publicar_fila import PublicarFila
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
from app.infrastructure.swalis_stub import SwalisStub
from app.infrastructure.verificador import VerificadorOficial


class VerificadorReprova:
    def verificar(self, caminho):
        return False, "reprovado"


def _publicar(session, tmp_path, verificador):
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                      SwalisStub(), ExportadorCsv(), settings.ref_date)
    return PublicarFila(gerar, verificador, SqlFilaRepository(session),
                        SqlUnidadeDeTrabalho(session),
                        lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()


def test_publica_941_linhas_e_falha_preserva_anterior(session, tmp_path):
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                 SqlUnidadeDeTrabalho(session)).executar()
    repo = SqlFilaRepository(session)
    assert repo.obter_publicada() == [] and repo.publicada_em() is None

    r = _publicar(session, tmp_path, VerificadorOficial())
    assert r.publicada
    publicada = repo.obter_publicada()
    assert len(publicada) == 941
    assert [l.posicao for l in publicada] == list(range(1, 942))
    assert repo.publicada_em() is not None

    r2 = _publicar(session, tmp_path, VerificadorReprova())
    assert not r2.publicada
    assert repo.obter_publicada() == publicada
