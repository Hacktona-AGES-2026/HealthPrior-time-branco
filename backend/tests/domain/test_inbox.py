"""US-12 · regras puras do inbox."""
from app.domain.enums import Classe, ClasseStatus
from app.domain.inbox import (
    chave_ordenacao,
    classe_implicita_prioridade,
    classe_referencia,
    distancia,
    entra_no_inbox,
)

NUNCA = ClasseStatus.SUGERIDA_NAO_CONFIRMADA
CONF = ClasseStatus.CONFIRMADA


def test_classe_implicita():
    assert classe_implicita_prioridade("alta") == Classe.B
    assert classe_implicita_prioridade("media") == Classe.C
    assert classe_implicita_prioridade("baixa") == Classe.D
    assert classe_implicita_prioridade(None) == Classe.D
    assert classe_implicita_prioridade("urgente") == Classe.D


def test_distancia_absoluta():
    assert distancia(Classe.A1, Classe.D) == 4
    assert distancia(Classe.D, Classe.A1) == 4
    assert distancia(Classe.B, Classe.B) == 0
    assert distancia(Classe.B, Classe.C) == 1


def test_nunca_confirmado_entra_com_distancia_2_ou_mais():
    assert entra_no_inbox(Classe.B, NUNCA, None, "baixa")      # D->B = 2
    assert entra_no_inbox(Classe.A2, NUNCA, None, "baixa")     # D->A2 = 3
    assert not entra_no_inbox(Classe.C, NUNCA, None, "baixa")  # 1
    assert not entra_no_inbox(Classe.D, NUNCA, None, "baixa")  # 0


def test_nunca_confirmado_para_baixo_tambem_entra():
    assert entra_no_inbox(Classe.D, NUNCA, None, "alta")       # B->D = 2
    assert not entra_no_inbox(Classe.C, NUNCA, None, "alta")   # 1


def test_confirmado_entra_com_qualquer_mudanca():
    assert entra_no_inbox(Classe.C, CONF, Classe.B, "baixa")
    assert entra_no_inbox(Classe.A1, CONF, Classe.A2, None)
    assert not entra_no_inbox(Classe.B, CONF, Classe.B, "baixa")


def test_classe_referencia():
    assert classe_referencia(CONF, Classe.A2, "baixa") == Classe.A2
    assert classe_referencia(NUNCA, None, "media") == Classe.C
    assert classe_referencia(CONF, None, "alta") == Classe.B


def test_ordenacao():
    itens = [("d", chave_ordenacao(Classe.B, 2, 1)),
             ("a", chave_ordenacao(Classe.A1, 1, 9)),
             ("c", chave_ordenacao(Classe.B, 3, 5)),
             ("e", chave_ordenacao(Classe.B, 2, 0))]
    assert [n for n, _ in sorted(itens, key=lambda p: p[1])] == ["a", "c", "e", "d"]
