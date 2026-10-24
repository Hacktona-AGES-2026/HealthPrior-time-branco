from datetime import date

import pytest

from app.domain.enums import Classe
from app.domain.models import Evento
from app.domain.swalis import (
    CategoriaSinal,
    SinalTexto,
    classificar,
    cruzar_eixos,
    eixo_progressao,
    eixo_sintoma,
    sinais_por_palavra_chave,
    validar_sinal_llm,
)
from app.domain.texto import buscar_termos, localizar_trecho
from app.domain.swalis import TERMOS

# Kit de negação (SW-04): as 10 hérnias K40.9 do dataset com "Sem sinais de encarceramento".
HERNIAS_NEGADAS = {
    "SOL-2026-00239": "Hernia inguinal bilateral redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2024-00050": "Hernia inguinal esquerda redutivel, abaulamento aos esforcos. Sem sinais de encarceramento. ICC compensada, FE preservada em eco recente.",
    "SOL-2026-00797": "Hernia inguinal esquerda redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2026-00448": "Hernia inguinal bilateral redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2023-00058": "Hernia inguinal direita redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2025-00123": "Hernia inguinal direita redutivel, abaulamento aos esforcos. Sem sinais de encarceramento. Hipertenso em uso de losartana.",
    "SOL-2024-00152": "Hernia inguinal direita redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2026-00838": "Hernia inguinal direita redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
    "SOL-2026-00343": "Hernia inguinal esquerda redutivel, abaulamento aos esforcos. Sem sinais de encarceramento. Diabetica, ultima HbA1c em anexo.",
    "SOL-2025-00322": "Hernia inguinal bilateral redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.",
}


def _risco(trecho: str, origem: str = "regra") -> SinalTexto:
    return SinalTexto(CategoriaSinal.RISCO_VIDA, "x", trecho, "justificativa_clinica", origem)


@pytest.mark.parametrize("sid,texto", HERNIAS_NEGADAS.items())
def test_hernia_com_negacao_nao_vira_urgencia(sid, texto):
    sinais = sinais_por_palavra_chave(texto, "justificativa_clinica")
    assert sinais == [], sid
    assert eixo_progressao("K40.9", [], sinais).nivel == 0


@pytest.mark.parametrize("texto", [
    "Nega sangramento espontaneo.",
    "Ausência de icterícia.",
    "Não há sinais de estrangulamento.",
    "US descarta colangite.",
])
def test_outras_negacoes(texto):
    assert sinais_por_palavra_chave(texto, "j") == []


def test_negacao_nao_atravessa_frase_nem_oracao():
    # SOL com nevo: "sem sinais de malignidade" não nega o sangramento da frase seguinte.
    texto = ("Nevo melanocitico regiao malar, 1,5 cm, sem sinais de malignidade. "
             "Lesao com sangramento espontaneo e crescimento rapido.")
    termos = {s.termo for s in sinais_por_palavra_chave(texto, "j")}
    assert {"sangramento espontaneo", "crescimento rapido"} <= termos
    # Vírgula/adversativa encerra o escopo: a suboclusão continua valendo.
    assert sinais_por_palavra_chave("Sem melhora, evoluiu com suboclusao.", "j")


def test_sinal_traz_trecho_original():
    [oc] = buscar_termos("Obesa. Hérnia encarcerada com redução manual no PS.", TERMOS[CategoriaSinal.RISCO_VIDA])
    assert oc.trecho == "Hérnia encarcerada com redução manual no PS"


@pytest.mark.parametrize("cid,eventos,sinais,nivel", [
    ("K43.0", [], [], 3),  # obstrução
    ("K40.9", [], [_risco("hernia encarcerada")], 3),  # alarme no texto
    ("C50.4", [], [], 2),  # SOL-2025-00048
    ("K80.2", [Evento("E1", "S", "P", date(2026, 1, 1), "biopsia", "positivo")], [], 2),
    ("C44.3", [Evento("E1", "S", "P", date(2026, 1, 1), "biopsia", "positivo")], [], 1),
    ("D37.4", [], [], 1),
    ("R91", [], [], 1),
    ("K40.9", [], [], 0),
])
def test_eixo_progressao(cid, eventos, sinais, nivel):
    assert eixo_progressao(cid, eventos, sinais).nivel == nivel


@pytest.mark.parametrize("cid,dor,lim,nivel", [
    ("K40.9", 8, "leve", 2),
    ("K40.9", 2, "grave", 2),
    ("I83.2", 0, "nenhuma", 2),
    ("K40.9", 5, "leve", 1),
    ("K40.9", 1, "moderada", 1),
    ("K40.9", None, None, 1),  # nunca rebaixar por falta de dado
    ("K40.9", 2, None, 1),
    ("K40.9", 3, "leve", 0),
    ("K40.9", 0, "nenhuma", 0),
])
def test_eixo_sintoma(cid, dor, lim, nivel):
    assert eixo_sintoma(cid, dor, lim, []).nivel == nivel


@pytest.mark.parametrize("prog,sint,classe", [
    (3, 0, Classe.A1), (2, 0, Classe.A2), (1, 0, Classe.B),
    (0, 2, Classe.B), (0, 1, Classe.C), (0, 0, Classe.D), (3, 2, Classe.A1),
])
def test_cruzar_eixos(prog, sint, classe):
    assert cruzar_eixos(prog, sint) is classe


def test_oncologico_nunca_abaixo_de_b():
    for cid in ("C18.7", "C61", "C44.3"):
        assert classificar(cid, 0, "nenhuma", [], []).classe in (Classe.A1, Classe.A2, Classe.B)


def test_justificativa_mostra_os_dois_eixos():
    j = classificar("C61", 0, "nenhuma", [], []).justificativa()
    assert "progressão 2" in j and "sintoma 0" in j and "C61" in j


def test_sinal_llm_so_vale_com_trecho_literal_e_nao_negado():
    texto = "Hernia irredutivel nas ultimas semanas, dor em piora. Sem sinais de estrangulamento."
    assert validar_sinal_llm(_risco("hernia irredutivel nas ultimas semanas", "llm"), texto)
    assert validar_sinal_llm(_risco("HÉRNIA  irredutível", "llm"), texto)  # caixa/acento/espaço
    assert not validar_sinal_llm(_risco("hernia estrangulada", "llm"), texto)  # inventado
    assert not validar_sinal_llm(_risco("sinais de estrangulamento", "llm"), texto)  # negado
    assert not validar_sinal_llm(_risco("Sem sinais de estrangulamento", "llm"), texto)


def test_localizar_trecho():
    assert localizar_trecho("Dor 9/10. Irredutível.", "irredutivel") == (10, 21)
    assert localizar_trecho("abc", "") is None


def test_sinal_do_llm_nao_muda_a_classe():
    # I-05: a categoria vem do LLM; se mudasse a classe, o LLM estaria decidindo.
    c = classificar("K40.9", 0, "nenhuma", [], [_risco("Paciente com hernia", "llm")])
    assert c.classe is Classe.D and c.progressao.nivel == 0


def test_frases():
    from app.domain.texto import frases
    assert frases("Hernia redutivel. Sem sinais de encarceramento.\nDor 4; ok") == [
        "Hernia redutivel", "Sem sinais de encarceramento", "Dor 4", "ok"]


def test_suspeita_de_malignidade_em_cancer_confirmado_e_redundante():
    from app.domain.swalis import alerta_redundante
    sinal = SinalTexto(CategoriaSinal.SUSPEITA_MALIGNIDADE, "x", "Nodulo BI-RADS 4C", "j", "llm")
    assert alerta_redundante(sinal, "C50.4")
    assert not alerta_redundante(sinal, "D44.0")
    assert not alerta_redundante(_risco("Lesao de tronco 80%", "llm"), "C61")
