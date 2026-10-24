import pytest

from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe
from app.domain.fatores import (
    TETO_FATOR,
    CelulaIrr,
    calcular_fatores,
    categorias_charlson,
    chave_irr,
    faixa_idade,
    fator_comorbidade,
    fator_idade,
)


def test_charlson_le_texto_e_cid_secundario_e_conta_categoria_uma_vez():
    achadas = categorias_charlson("HAS; DM2; ICC", "E11.9; I50.0")
    assert achadas == {"diabetes_sem_complicacao": "texto:dm2",
                       "insuficiencia_cardiaca": "texto:icc"}


def test_charlson_hierarquia_metastase_substitui_tumor():
    achadas = categorias_charlson(None, "C50.9; C78.0")
    assert set(achadas) == {"metastatico"}
    assert fator_comorbidade(None, "C50.9; C78.0")[0].regra == "charlson_6"


@pytest.mark.parametrize("comorbidades,esperado", [
    ("nenhuma", 1.00),
    ("dm2", 1.03),            # 1 ponto
    ("drc", 1.06),            # 2 pontos
    ("icc; drc; dm2", 1.10),  # 4 pontos (faixa 3–4)
    ("icc; drc; dm2; dpoc", 1.15),  # 5 pontos (faixa >= 5)
])
def test_fator_comorbidade_por_faixa(comorbidades, esperado):
    assert fator_comorbidade(comorbidades, None)[0].valor == esperado


def test_cid_principal_nao_conta_como_comorbidade():
    f = calcular_fatores("C18.7", 70, None, None, None)
    assert f.comorbidade.valor == 1.0 and f.categorias_charlson == []


@pytest.mark.parametrize("idade,faixa", [(0, "0-17"), (17, "0-17"), (18, "18-39"), (49, "40-49"),
                                         (79, "70-79"), (80, "80+"), (None, None)])
def test_faixa_idade(idade, faixa):
    assert faixa_idade(idade) == faixa


@pytest.mark.parametrize("celula,valor,regra", [
    (None, 1.0, "neutro_irr_indisponivel"),
    (CelulaIrr(None, 0), 1.0, "neutro_irr_indisponivel"),
    (CelulaIrr(8.0, 19), 1.0, "neutro_poucos_obitos"),  # CDC/NCHS: < 20 óbitos
    (CelulaIrr(0.8, 500), 1.0, "neutro_irr_ate_1"),
    (CelulaIrr(2.0, 500), 1.075, "ajuste_log2_irr"),    # uma duplicação
    (CelulaIrr(4.0, 500), 1.15, "ajuste_log2_irr"),     # satura em IRR 4
    (CelulaIrr(30.0, 500), 1.15, "ajuste_log2_irr"),
])
def test_fator_idade(celula, valor, regra):
    f = fator_idade("C18.7", 75, celula)
    assert (f.valor, f.regra) == (valor, regra)


def test_chave_irr_usa_cid3_e_faixa():
    assert chave_irr("C18.7", 75) == ("C18", "70-79")
    assert chave_irr("C18.7", None) is None


def test_teto_nao_inverte_classes_vizinhas_com_o_mesmo_tempo():
    """1,15 × 1,15 < menor razão entre prazos vizinhos: fator nunca troca a ordem das classes."""
    ordem = [Classe.A1, Classe.A2, Classe.B, Classe.C, Classe.D]
    menor_razao = min(PRAZO_MAXIMO_DIAS[b] / PRAZO_MAXIMO_DIAS[a] for a, b in zip(ordem, ordem[1:]))
    assert TETO_FATOR * TETO_FATOR < menor_razao
