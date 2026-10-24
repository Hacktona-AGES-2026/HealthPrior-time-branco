"""PRE-12 · Tabela CID-10 do DATASUS: validação e busca usadas pela sugestão de CID (D-117)."""
import pytest

from app.config import settings
from app.infrastructure.tabela_cid import tabela_cid

pytestmark = pytest.mark.skipif(
    not (settings.data_dir / "referencias" / "CID10CSV" / "CID-10-SUBCATEGORIAS.CSV").exists(),
    reason="tabela CID-10 ausente")


@pytest.fixture(scope="module")
def tabela():
    return tabela_cid(settings.data_dir)


@pytest.mark.parametrize("cid", ["C50.9", "C509", "c50.9 ", "C73"])
def test_codigos_existentes_com_ou_sem_ponto(tabela, cid):
    assert tabela.descricao(cid)


def test_codigo_inexistente(tabela):
    assert tabela.descricao("C99.9") is None


def test_busca_acha_o_orgao_sem_acento(tabela):
    codigos = [c for c, _ in tabela.buscar("neoplasia maligna mama")]
    assert "C50.9" in codigos


def test_busca_so_devolve_codigo_folha(tabela):
    # C50 tem subcategorias: a busca devolve C50.x, nunca a categoria sozinha
    assert "C50" not in [c for c, _ in tabela.buscar("neoplasia maligna mama", limite=50)]


def test_busca_vazia(tabela):
    assert tabela.buscar("de a") == []
