import pytest

from app.domain.cid import is_cid_urgente, is_lesao_incerta, is_oncologico, normalizar_cid


@pytest.mark.parametrize("entrada,esperado", [("K40.9", "K409"), ("k409 ", "K409"), ("C18.7", "C187"),
                                              ("", ""), (None, "")])
def test_normalizar_cid(entrada, esperado):
    assert normalizar_cid(entrada) == esperado


def test_oncologico_usa_cid_nao_flag():
    # SOL-2025-00149: C61 com flag "nao" -> oncológico
    assert is_oncologico("C61")
    # SOL-2026-00583: K40.9 com flag "sim" -> não oncológico
    assert not is_oncologico("K40.9")


@pytest.mark.parametrize("cid,esperado", [("D37.4", True), ("D48.6", True), ("D36.9", False),
                                          ("R91", True), ("D24", False)])
def test_lesao_incerta(cid, esperado):
    assert is_lesao_incerta(cid) is esperado


def test_cid_urgente():
    assert is_cid_urgente("K40.3")
    assert not is_cid_urgente("K40.9")
