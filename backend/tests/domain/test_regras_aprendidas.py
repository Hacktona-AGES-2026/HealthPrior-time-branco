"""US-19 · regra aprendida (procedimento + classe_de → classe_para) e shadow run."""
from datetime import date

from app.domain.enums import Classe
from app.domain.models import Solicitacao
from app.domain.regras_aprendidas import RegraAprendida, aplicar_regras, simular_impacto, versao_atual


def sol(sid, proc="PROC004", cid="K80.2"):
    s = Solicitacao.__new__(Solicitacao)
    s.__dict__.update(solicitacao_id=sid, procedimento_id=proc, cid_norm=cid.replace(".", ""), cid_principal=cid)
    return s


R = RegraAprendida("PROP-1", "PROC004", Classe.C, Classe.B, 1)


def test_regra_troca_a_classe_so_se_procedimento_e_classe_de_batem():
    assert aplicar_regras(sol("A"), Classe.C, [R]) == (Classe.B, R)
    assert aplicar_regras(sol("A"), Classe.D, [R]) == (Classe.D, None)
    assert aplicar_regras(sol("A", proc="PROC002"), Classe.C, [R]) == (Classe.C, None)


def test_rebaixar_nunca_vale_para_oncologico():
    rebaixa = RegraAprendida("PROP-2", "PROC004", Classe.B, Classe.C, 2)
    assert aplicar_regras(sol("A", cid="C50.4"), Classe.B, [rebaixa]) == (Classe.B, None)
    assert aplicar_regras(sol("A"), Classe.B, [rebaixa]) == (Classe.C, rebaixa)
    # subir vale para oncológico
    assert aplicar_regras(sol("A", cid="C50.4"), Classe.C, [R]) == (Classe.B, R)


def test_vale_a_regra_de_maior_versao():
    nova = RegraAprendida("PROP-3", "PROC004", Classe.C, Classe.A2, 3)
    assert aplicar_regras(sol("A"), Classe.C, [R, nova])[0] == Classe.A2
    assert versao_atual([R, nova]) == 3 and versao_atual([]) == 0


def test_shadow_run_conta_afetados_e_oncologicos_sem_rebaixar():
    cands = [(sol("A"), Classe.C), (sol("B"), Classe.C), (sol("C"), Classe.D),
             (sol("D", cid="C50.4"), Classe.C), (sol("E", proc="PROC002"), Classe.C)]
    imp = simular_impacto(cands, R)
    assert (imp.afetados, imp.oncologicos_afetados, imp.oncologicos_rebaixados) == (3, 1, 0)
    assert imp.ids == ["A", "B", "D"] and imp.exemplos == ["A", "B", "D"]


def test_shadow_run_de_rebaixa_poupa_oncologico():
    rebaixa = RegraAprendida("P", "PROC004", Classe.B, Classe.C, 1)
    imp = simular_impacto([(sol("A"), Classe.B), (sol("O", cid="C50.4"), Classe.B)], rebaixa)
    assert (imp.afetados, imp.oncologicos_afetados, imp.oncologicos_rebaixados) == (1, 0, 0)
