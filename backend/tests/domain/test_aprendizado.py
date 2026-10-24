from datetime import datetime, timedelta, timezone

from app.domain.aprendizado import (CasoAprendizado, ParametrosAprendizado, agrupar, direcao,
                                    proposta_id)
from app.domain.enums import Classe, MotivoCodificado

REF = datetime(2026, 10, 24, tzinfo=timezone.utc)
M = MotivoCodificado.PS_RECORRENTE
P = ParametrosAprendizado()


def _caso(i, reg="reg-01", de=Classe.C, para=Classe.B, dias=10, proc="PROC004", motivo=M):
    return CasoAprendizado(f"D{i:03d}", f"S{i}", reg, REF - timedelta(days=dias), proc, motivo, de, para)


def _passam(n=5):
    return [_caso(i, f"reg-0{i % 3 + 1}") for i in range(n)]


def test_direcao_e_id():
    assert direcao(Classe.C, Classe.B) == "subir"
    assert direcao(Classe.B, Classe.C) == "rebaixar"
    assert direcao(Classe.B, Classe.B) is None
    assert proposta_id("PROC004", M, Classe.C, Classe.B) == "PROP-PROC004-ps_recorrente-C-B"


def test_passa_todos_os_filtros():
    [p] = agrupar(_passam(), REF, P, set())
    assert (p.proposta_id, p.direcao, p.n_casos, p.n_reguladores, p.consistencia, p.status) == \
        ("PROP-PROC004-ps_recorrente-C-B", "subir", 5, 3, 1.0, "pendente")
    assert p.casos == sorted(p.casos)


def test_falha_volume():
    assert agrupar(_passam(4), REF, P, set()) == []


def test_falha_reguladores():
    assert agrupar([_caso(i, f"reg-0{i % 2 + 1}") for i in range(6)], REF, P, set()) == []


def test_falha_janela_e_naive_tratado_como_utc():
    assert agrupar([_caso(i, f"reg-0{i % 3 + 1}", dias=120) for i in range(6)], REF, P, set()) == []
    naive = [CasoAprendizado(c.decisao_id, c.solicitacao_id, c.regulador_id, c.data.replace(tzinfo=None),
                             c.procedimento_id, c.motivo, c.classe_de, c.classe_para) for c in _passam()]
    assert len(agrupar(naive, REF.replace(tzinfo=None), P, set())) == 1


def test_consistencia_conta_manter_no_denominador():
    casos = [_caso(i, f"reg-0{i % 3 + 1}") for i in range(8)] + [_caso(9, "reg-02", para=Classe.C)]
    [p] = agrupar(casos, REF, P, set())
    assert p.consistencia == 0.89
    casos += [_caso(10, "reg-02", para=Classe.C), _caso(11, "reg-02", para=Classe.C)]  # 8/11 = 0.73
    assert agrupar(casos, REF, P, set()) == []


def test_descarte_i01_so_rebaixa_com_onco():
    reb = [_caso(i, f"reg-0{i % 3 + 1}", de=Classe.B, para=Classe.C) for i in range(6)]
    [p] = agrupar(reb, REF, P, {"PROC004"})
    assert p.status == "descartada" and p.direcao == "rebaixar" and "I-01" in p.motivo_descarte
    assert agrupar(reb, REF, P, set())[0].status == "pendente"
    [s] = agrupar(_passam(), REF, P, {"PROC004"})
    assert s.status == "pendente" and s.motivo_descarte is None


def test_ordenacao_pendentes_primeiro():
    desc = [_caso(i, f"reg-0{i % 3 + 1}", de=Classe.B, para=Classe.C, proc="PROC018") for i in range(8)]
    pend = [_caso(20 + i, f"reg-0{i % 3 + 1}") for i in range(5)]
    r = agrupar(desc + pend, REF, P, {"PROC018"})
    assert [p.status for p in r] == ["pendente", "descartada"]
