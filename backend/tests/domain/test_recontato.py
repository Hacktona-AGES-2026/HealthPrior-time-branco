"""US-17 · recontato de quem está sem evento (C-04, I-08)."""
from datetime import date

from app.domain.models import Evento, Solicitacao
from app.domain.recontato import REC_SEM_EVENTO, dias_sem_evento, detectar_recontato

HOJE = date(2026, 10, 23)


def sol(entrada=date(2026, 1, 1)):
    s = Solicitacao.__new__(Solicitacao)
    s.__dict__.update(solicitacao_id="S1", data_entrada_fila=entrada)
    return s


def ev(dia, **kw):
    return Evento("E", "S1", "P", dia, kw.pop("tipo", "contato_telefonico"), **kw)


def test_sem_evento_conta_desde_a_entrada_na_fila():
    assert dias_sem_evento(sol(date(2026, 1, 1)), [], HOJE) == (295, date(2026, 1, 1), "entrada na fila")
    a = detectar_recontato(sol(date(2026, 1, 1)), [], HOJE, 180)
    assert a.regra == REC_SEM_EVENTO and a.bloqueante is False and "295 dias" in a.titulo
    assert a.evidencias[0].fonte == "solicitacao" and a.evidencias[0].data == date(2026, 1, 1)


def test_conta_desde_o_ultimo_evento_e_o_limite_e_inclusivo():
    eventos = [ev(date(2026, 1, 10)), ev(date(2026, 4, 26))]  # último: 180 dias antes de HOJE
    assert detectar_recontato(sol(), eventos, HOJE, 180) is not None
    assert detectar_recontato(sol(), eventos, HOJE, 181) is None
    assert dias_sem_evento(sol(), eventos, HOJE)[2] == "último evento"


def test_evento_recente_ou_na_entrada_nao_gera():
    assert detectar_recontato(sol(), [ev(date(2026, 10, 1))], HOJE, 180) is None
    assert detectar_recontato(sol(date(2026, 9, 1)), [], HOJE, 180) is None


def test_duplicado_orfao_e_futuro_nao_contam_como_evento():
    eventos = [ev(date(2026, 10, 1), duplicado_de="E0"), ev(date(2026, 10, 2), orfao=True),
               ev(date(2026, 11, 30))]  # futuro: relógio simulado ainda não chegou lá
    assert detectar_recontato(sol(), eventos, HOJE, 180) is not None


def test_evento_antes_da_entrada_nao_adia_o_recontato():
    # histórico: o paciente entrou depois; vale a entrada
    assert dias_sem_evento(sol(date(2026, 3, 1)), [ev(date(2025, 12, 1))], HOJE)[1] == date(2026, 3, 1)
