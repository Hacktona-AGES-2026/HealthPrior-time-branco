from datetime import date

from app.domain.metricas import (
    calcular_indicadores,
    com_ps_recente,
    is_sem_urgencia_verificador,
    ordem_atual,
)
from app.domain.models import Evento, Solicitacao


def sol(sid, prio=None, entrada=date(2026, 1, 1), cid="K409", onco=False, dor=None, lim=None,
        just="", prio_reg=None):
    return Solicitacao(solicitacao_id=sid, paciente_id="P", procedimento_id="X", cid_principal=cid,
                       data_entrada_fila=entrada, cid_norm=cid, oncologico=onco,
                       intensidade_dor_eva=dor, limitacao_funcional=lim, justificativa_clinica=just,
                       prioridade_norm=prio, prioridade_regulacao=prio_reg)


def ev(sid, tipo, data=date(2026, 5, 1), resultado=None):
    return Evento(evento_id="E", solicitacao_id=sid, paciente_id="P", data_evento=data,
                  tipo_evento=tipo, resultado=resultado)


def test_ordem_atual_prioridade_data_e_id():
    s = [sol("D"), sol("C", "baixa"), sol("B2", "media", date(2026, 1, 1)),
         sol("B1", "media", date(2026, 1, 1)), sol("B0", "media", date(2025, 1, 1)),
         sol("A", "alta", date(2026, 6, 1))]
    assert ordem_atual(s) == ["A", "B0", "B1", "B2", "C", "D"]


def test_ordem_atual_usa_prioridade_regulacao_quando_norm_vazia():
    s = [sol("X"), sol("Y", prio=None, prio_reg="Média"), sol("Z", prio=None, prio_reg="ALTA")]
    assert ordem_atual(s) == ["Z", "Y", "X"]


def test_indicadores_uma_violacao():
    ordem = ["a", "calmo", "onco1", "b", "c", "d"]
    r = calcular_indicadores(ordem, {"a", "onco1"}, {"calmo"}, set())
    assert r.violacoes_regra_ouro == 1
    assert r.total == 6


def test_indicadores_zero_violacoes_e_mediana():
    ordem = ["o1", "o2", "o3", "o4", "calmo", "x"]
    r = calcular_indicadores(ordem, {"o1", "o2", "o3", "o4"}, {"calmo"}, set())
    assert r.violacoes_regra_ouro == 0
    assert r.posicao_mediana_oncologicos == 2.5
    assert r.pct_oncologicos_primeiro_terco == 50.0  # posições 1 e 2 (<= 2)


def test_indicadores_percentuais():
    ordem = [str(i) for i in range(1, 10)]  # n = 9: terço = 3, metade = 4.5, 2n/3 = 6
    r = calcular_indicadores(ordem, {"1", "5", "9"}, {"6", "7", "8", "9"}, {"2", "5", "9"})
    assert r.pct_oncologicos_primeiro_terco == 33.3
    assert r.pct_ps_recente_primeira_metade == 33.3
    assert r.pct_sem_urgencia_ultimo_terco == 75.0  # 7, 8, 9 de 4


def test_indicadores_vazios():
    r = calcular_indicadores([], set(), set(), set())
    assert (r.total, r.violacoes_regra_ouro, r.posicao_mediana_oncologicos) == (0, 0, None)
    assert r.pct_oncologicos_primeiro_terco == r.pct_ps_recente_primeira_metade == 0.0
    assert r.pct_sem_urgencia_ultimo_terco == 0.0


def test_com_ps_recente():
    ref = date(2026, 10, 23)
    eventos = {"A": [ev("A", "pronto_socorro", date(2026, 8, 1))],
               "B": [ev("B", "internacao", date(2025, 1, 1))],
               "C": [ev("C", "consulta_reavaliacao", date(2026, 9, 1), "piora")],
               "D": [ev("D", "internacao", date(2026, 4, 26))]}  # exatamente 180 dias
    assert com_ps_recente(eventos, ref) == {"A", "D"}


def test_sem_urgencia_basico():
    assert is_sem_urgencia_verificador(sol("A"), [])
    assert is_sem_urgencia_verificador(sol("A", dor=3, lim="leve"), [])


def test_sem_urgencia_dor_4_nao():
    assert not is_sem_urgencia_verificador(sol("A", dor=4), [])


def test_sem_urgencia_onco_nunca():
    assert not is_sem_urgencia_verificador(sol("A", cid="C61", onco=True), [])


def test_sem_urgencia_ps_antes_da_entrada_ainda_conta():
    e = ev("A", "pronto_socorro", date(2020, 1, 1))
    assert not is_sem_urgencia_verificador(sol("A", entrada=date(2026, 1, 1)), [e])


def test_sem_urgencia_outros_bloqueios():
    assert not is_sem_urgencia_verificador(sol("A", cid="K403"), [])
    assert not is_sem_urgencia_verificador(sol("A", lim="moderada"), [])
    assert not is_sem_urgencia_verificador(sol("A", just="Paciente com colangite"), [])
    assert not is_sem_urgencia_verificador(sol("A"), [ev("A", "biopsia", resultado="positivo")])
    assert is_sem_urgencia_verificador(sol("A"), [ev("A", "biopsia", resultado="negativo")])


def test_espelho_do_verificador_ignora_negacao():
    # O verificador oficial não trata negação: "Sem sinais de encarceramento" é urgente para ele,
    # mesmo que a fila (D-122) não conte. A comparação antes × depois tem de seguir o verificador.
    from datetime import date
    from app.domain.metricas import is_sem_urgencia_verificador
    from app.domain.models import Solicitacao
    s = Solicitacao("S1", "P", "PR", "K40.9", date(2026, 1, 1), intensidade_dor_eva=2,
                    limitacao_funcional="leve",
                    justificativa_clinica="Hernia redutivel. Sem sinais de encarceramento.")
    assert is_sem_urgencia_verificador(s, []) is False
