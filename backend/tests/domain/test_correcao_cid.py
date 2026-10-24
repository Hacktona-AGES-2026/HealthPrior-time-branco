"""PRE-12 · D-117: validação da sugestão de CID e aplicação da correção (funções puras)."""
from datetime import date

import pytest

from app.domain.correcao_cid import aplicar_correcao_cid, motivo_rejeicao
from app.domain.errors import ResolucaoInvalidaError
from app.domain.models import Solicitacao, SugestaoCid

LAUDO = "Resultado de biopsia: carcinoma papilifero."


def sugestao(cid="C18.9", citacao="carcinoma papilifero"):
    return SugestaoCid(cid=cid, descricao="Neoplasia maligna do cólon", citacao=citacao, confianca=0.9,
                       modelo="falso")


def sol(cid="D37.4"):
    return Solicitacao(solicitacao_id="SOL-1", paciente_id="P-1", procedimento_id="PROC-1",
                       cid_principal=cid, data_entrada_fila=date(2025, 1, 1),
                       cid_descricao="Neoplasia de comportamento incerto do cólon", cid_norm=cid.replace(".", ""))


def test_sugestao_valida_passa():
    assert motivo_rejeicao(sugestao(), LAUDO, "D37.4", "Neoplasia maligna do cólon") is None


def test_citacao_compara_sem_caixa_nem_espacos_extras():
    assert motivo_rejeicao(sugestao(citacao="  CARCINOMA   papilifero "), LAUDO, "D37.4", "x") is None


@pytest.mark.parametrize("sug, cid_atual, descricao, motivo", [
    (sugestao(), "D37.4", None, "não existe"),
    (sugestao(cid="D37.4"), "D374", "x", "mesmo"),
    (sugestao(citacao="adenocarcinoma invasivo"), "D37.4", "x", "literalmente"),
    (sugestao(citacao=""), "D37.4", "x", "literalmente"),
])
def test_sugestao_invalida_e_descartada(sug, cid_atual, descricao, motivo):
    assert motivo in motivo_rejeicao(sug, LAUDO, cid_atual, descricao)


def test_correcao_vale_para_tudo_e_guarda_o_original():
    s = sol()

    correcao = aplicar_correcao_cid(s, "C18.9", "Neoplasia maligna do cólon, não especificado")

    assert (s.cid_principal, s.cid_norm, s.cid_confirmado, s.cid_original) == ("C18.9", "C189", "C18.9", "D37.4")
    assert s.oncologico is True  # I-09: pelo CID
    assert s.cid_descricao == "Neoplasia maligna do cólon, não especificado"
    assert (correcao.campo, correcao.original, correcao.novo, correcao.regra) == (
        "cid_principal", "D37.4", "C18.9", "PRE-12")


def test_segunda_correcao_mantem_o_original_do_cadastro():
    s = sol()
    aplicar_correcao_cid(s, "C18.9", "cólon")

    correcao = aplicar_correcao_cid(s, "C20", "reto")

    assert s.cid_original == "D37.4" and (correcao.original, correcao.novo) == ("C18.9", "C20")


def test_corrigir_para_o_mesmo_cid_e_recusado():
    with pytest.raises(ResolucaoInvalidaError):
        aplicar_correcao_cid(sol(), "D374", "mesmo CID sem ponto")


def test_citacao_curta_demais_e_descartada():
    assert "literalmente" in motivo_rejeicao(sugestao(citacao="ca"), LAUDO, "D37.4", "x")


def test_nao_troca_oncologico_por_cid_nao_oncologico():
    """I-02: a PRE-12 acha câncer; nunca tira alguém do grupo oncológico."""
    with pytest.raises(ResolucaoInvalidaError):
        aplicar_correcao_cid(sol("C18.9"), "K40.9", "Hérnia inguinal")
