from __future__ import annotations

from datetime import date

from app.application.montar_fila import linhas_para_dicts, montar_fila, montar_justificativa
from app.domain.enums import Classe, StatusFila
from app.domain.models import Evento, ResultadoScore, Solicitacao

REF = date(2026, 10, 23)


class ScorerFalso:
    versao_regras = "falso-1"

    def __init__(self, scores: dict[str, float], classe: Classe = Classe.C):
        self.scores, self.classe = scores, classe

    def calcular(self, solicitacao, eventos):
        s = self.scores.get(solicitacao.solicitacao_id, 0.0)
        return ResultadoScore(self.classe, 180, s, s, [], self.versao_regras)


def sol(sid, cid="K40.9", onco=False, **kw):
    base = dict(solicitacao_id=sid, paciente_id="P", procedimento_id="PR", cid_principal=cid,
                data_entrada_fila=date(2026, 1, 1), cid_norm=cid.replace(".", ""),
                oncologico=onco, intensidade_dor_eva=1, limitacao_funcional="nenhuma",
                justificativa_clinica="Quadro estavel.")
    base.update(kw)
    return Solicitacao(**base)


def evt(sid, tipo, resultado=None, data=date(2026, 5, 1), eid="E1"):
    return Evento(eid, sid, "P", data, tipo, resultado)


def por_id(linhas):
    return {l.solicitacao_id: l for l in linhas}


def test_oncologico_com_score_menor_fica_acima_de_nao_urgente():
    s = [sol("A"), sol("B", "C50.4", onco=True)]
    linhas = montar_fila(s, {}, ScorerFalso({"A": 90, "B": 10}), REF)
    assert [l.solicitacao_id for l in linhas] == ["B", "A"]
    assert linhas[0].camada == 1 and linhas[1].camada == 3


def test_dor_sozinha_fica_na_camada_3_com_sintoma_na_justificativa():
    # D-27: dor é sintoma (SWALIS), não sinal clínico de urgência.
    s = [sol("A"), sol("B", intensidade_dor_eva=8)]
    l = por_id(montar_fila(s, {}, ScorerFalso({"A": 90, "B": 5}), REF))
    assert l["B"].camada == 3
    assert l["A"].posicao == 1  # dentro da camada, quem ordena é o score
    assert "Camada 3: sem sinais clínicos de urgência. Sintomas: dor EVA 8." in l["B"].justificativa


def test_biopsia_positiva_antiga_nao_oncologico_camada_2_revisar_cid():
    s = [sol("A")]
    ev = {"A": [evt("A", "biopsia", "positivo", date(2020, 1, 1))]}
    l = por_id(montar_fila(s, ev, ScorerFalso({}), REF))
    assert l["A"].camada == 2
    assert "revisar CID" in l["A"].justificativa


def test_pronto_socorro_antes_da_entrada_nao_torna_urgente():
    s = [sol("A")]
    ev = {"A": [evt("A", "pronto_socorro", None, date(2025, 6, 1))]}
    l = por_id(montar_fila(s, ev, ScorerFalso({}), REF))
    assert l["A"].camada == 3
    assert "sem sinais clínicos de urgência" in l["A"].justificativa


def test_score_medico_substitui_score_sistema():
    s = [sol("A", score_medico=99.0, classe_medico=Classe.A1, editado_manualmente=True),
         sol("B")]
    linhas = montar_fila(s, {}, ScorerFalso({"A": 1, "B": 50}), REF)
    l = por_id(linhas)
    assert l["A"].score_efetivo == 99.0 and l["A"].classe == "A1"
    assert l["A"].posicao == 1
    assert "Editado manualmente pelo regulador." in l["A"].justificativa
    assert linhas_para_dicts(linhas)[0]["solicitacao_id"] == "A"


def test_classe_editada_recalcula_o_pct_com_o_prazo_da_classe_decidida():
    # 10 dias em fila, classe A1 (prazo 15): 66,7%, não o % do prazo da classe do sistema (180 dias)
    s = [sol("A", classe_medico=Classe.A1, editado_manualmente=True, data_entrada_fila=date(2026, 10, 13))]
    l = montar_fila(s, {}, ScorerFalso({"A": 5.6}), REF)[0]
    assert l.pct_prazo_consumido == 66.7
    assert "prazo 15 dias" in l.justificativa and "66.7% do prazo" in l.justificativa


def test_suspensa_nao_aparece():
    s = [sol("A"), sol("B", status_fila=StatusFila.SUSPENSA)]
    assert [l.solicitacao_id for l in montar_fila(s, {}, ScorerFalso({}), REF)] == ["A"]


def test_justificativa_camada_1_contem_cid():
    l = montar_fila([sol("A", "C61", onco=True)], {}, ScorerFalso({}), REF)[0]
    assert l.justificativa.startswith("Camada 1: oncológico pelo CID C61.")
    assert "Classe C (prazo 180 dias, regras falso-1)" in l.justificativa


def test_montar_justificativa_multiplos_motivos():
    s = sol("A", "K40.3", intensidade_dor_eva=7, limitacao_funcional="grave")
    t = montar_justificativa(2, s, ["cid_complicacao"], "B", 60,
                             "v1", 10, 16.7, sintomas=["dor", "limitacao"])
    assert t.startswith("Camada 2: urgente (CID de complicação K40.3). "
                        "Sintomas: dor EVA 7; limitação funcional grave.")
    assert t.endswith("10 dias em fila, 16.7% do prazo.")
