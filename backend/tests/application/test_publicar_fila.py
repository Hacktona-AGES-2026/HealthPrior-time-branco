"""US-10 · PublicarFila e ExportarFilaPublicada com falsos (sem banco)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.application.gerar_fila import ResultadoGeracao
from app.application.publicar_fila import ExportarFilaPublicada, PublicarFila
from app.domain.errors import FilaNaoPublicadaError
from app.domain.models import LinhaFila

AGORA = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
REF = date(2026, 10, 23)


def _linha(i: int) -> LinhaFila:
    return LinhaFila(solicitacao_id=f"SOL-{i}", posicao=i, justificativa="j", camada=1,
                     classe="A", pct_prazo_consumido=0.5, dias_em_fila=10, score_efetivo=1.0,
                     editado_manualmente=False, versao_regras="v1")


class GerarFalso:
    def __init__(self):
        self.linhas = [_linha(1), _linha(2)]

    def executar(self, caminho: Path) -> ResultadoGeracao:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("solicitacao_id,posicao,justificativa\nSOL-1,1,j\nSOL-2,2,j\n")
        return ResultadoGeracao(self.linhas, caminho, 2, "v1", {1: 2}, REF)


class VerificadorFalso:
    def __init__(self, passa: bool):
        self.passa = passa

    def verificar(self, caminho):
        return self.passa, "saida"


class FilaFalsa:
    def __init__(self, publicada=None, erro: Exception | None = None):
        self.chamadas = []
        self.publicada = publicada or []
        self.erro = erro

    def salvar_publicada(self, linhas, versao_regras, publicada_em, data_referencia):
        if self.erro:
            raise self.erro
        self.chamadas.append((linhas, versao_regras, publicada_em, data_referencia))

    def obter_publicada(self):
        return self.publicada

    def publicada_em(self):
        return None


class UowFalsa:
    def __init__(self):
        self.confirmou = 0
        self.desfez = 0

    def confirmar(self):
        self.confirmou += 1

    def desfazer(self):
        self.desfez += 1


def _caso(tmp_path, passa=True, fila=None):
    gerar = GerarFalso()
    fila = fila or FilaFalsa()
    uow = UowFalsa()
    caso = PublicarFila(gerar, VerificadorFalso(passa), fila, uow, lambda: AGORA, tmp_path)
    return caso, gerar, fila, uow


def test_verificador_ok_publica_e_promove_arquivo(tmp_path):
    caso, gerar, fila, uow = _caso(tmp_path)
    r = caso.executar()
    assert r.publicada and r.total == 2 and r.saida_verificador == "saida"
    assert fila.chamadas == [(gerar.linhas, "v1", AGORA, REF)]
    assert r.data_referencia == REF
    assert uow.confirmou == 1 and uow.desfez == 0
    final = tmp_path / "fila_priorizada.csv"
    assert r.caminho_csv == final
    assert final.read_text() == (tmp_path / "fila_priorizada.candidata.csv").read_text()


def test_verificador_falha_nao_publica_e_preserva_anterior(tmp_path):
    final = tmp_path / "fila_priorizada.csv"
    final.write_text("antigo")
    caso, _, fila, uow = _caso(tmp_path, passa=False)
    r = caso.executar()
    assert not r.publicada
    assert fila.chamadas == [] and uow.confirmou == 0 and uow.desfez == 1
    assert final.read_text() == "antigo"
    assert r.caminho_csv == tmp_path / "fila_priorizada.candidata.csv"


def test_excecao_no_salvar_desfaz_e_relanca(tmp_path):
    caso, _, _, uow = _caso(tmp_path, fila=FilaFalsa(erro=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        caso.executar()
    assert uow.desfez == 1 and uow.confirmou == 0
    assert not (tmp_path / "fila_priorizada.csv").exists()


class ExportadorFalso:
    def exportar(self, linhas, caminho):
        caminho.write_text(f"{len(linhas)} linhas")
        return caminho


def test_exportar_vazia_levanta(tmp_path):
    with pytest.raises(FilaNaoPublicadaError):
        ExportarFilaPublicada(FilaFalsa(), ExportadorFalso(), tmp_path).executar()


def test_exportar_com_linhas(tmp_path):
    caminho = ExportarFilaPublicada(FilaFalsa(publicada=[_linha(1), _linha(2)]),
                                    ExportadorFalso(), tmp_path).executar()
    assert caminho == tmp_path / "fila_publicada.csv"
    assert caminho.read_text() == "2 linhas"
