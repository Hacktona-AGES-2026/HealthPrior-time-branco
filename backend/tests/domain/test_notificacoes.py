"""Notificações ao paciente (demo): texto genérico e quem vale avisar."""
import pytest

from app.domain.notificacoes import POSICAO, RECONTATO, SITUACAO, mudancas_de_posicao, texto


def test_textos_sao_genericos_e_dizem_de_quem_seria():
    for motivo in (POSICAO, SITUACAO, RECONTATO):
        t = texto(motivo, "SOL-2023-00060", subiu=True)
        assert t.startswith("[DEMO SOL-2023-00060] HealthPrior: ")
        assert not any(p in t.lower() for p in ("classe", "score", "a1", "oncolog"))
    assert "subiu" in texto(POSICAO, "S", subiu=True) and "desceu" in texto(POSICAO, "S", subiu=False)
    assert all(ord(c) < 128 for c in texto(POSICAO, "S", True))  # cabe em SMS GSM-7


def test_motivo_desconhecido_e_erro():
    with pytest.raises(ValueError):
        texto("outro", "S")


def test_so_avisa_quem_mudou_o_minimo_e_as_maiores_mudancas_primeiro():
    antes = {"A": 10, "B": 20, "C": 30, "D": 40, "SAIU": 50}
    depois = {"A": 11, "B": 5, "C": 80, "D": 41, "NOVO": 1}
    assert mudancas_de_posicao(antes, depois, minimo=10, maximo=5) == [("C", False), ("B", True)]
    assert mudancas_de_posicao(antes, depois, minimo=10, maximo=1) == [("C", False)]
    assert mudancas_de_posicao(antes, depois, minimo=1, maximo=10)[2:] == [("A", False), ("D", False)]  # A e D: delta 1
    # quem saiu ou entrou na fila não é "mudou de lugar": tem outro motivo
    assert all(sid not in ("SAIU", "NOVO") for sid, _ in mudancas_de_posicao(antes, depois, 1, 10))
