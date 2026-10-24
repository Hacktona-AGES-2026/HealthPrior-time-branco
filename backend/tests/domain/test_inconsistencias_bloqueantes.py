"""PRE-20..PRE-25 (US-04): regras puras, sem banco. Casos e textos copiados do dataset real."""
from datetime import date

import pytest

from app.domain.models import Evento, Solicitacao
from app.domain.preprocessing.inconsistencias import (
    REGRAS_BLOQUEANTES,
    detectar_bloqueantes,
    detectar_eventos_orfaos,
)


def solicitacao(sol_id="SOL-X", paciente="PAC-X", proc="PROC003", entrada=date(2025, 9, 19), **kw):
    base = dict(solicitacao_id=sol_id, paciente_id=paciente, procedimento_id=proc,
                cid_principal="K42.9", data_entrada_fila=entrada, observacoes="")
    base.update(kw)
    return Solicitacao(**base)


def evento(evento_id="EVT-1", resultado="desistiu", tipo="contato_telefonico", data=date(2026, 3, 1), **kw):
    base = dict(evento_id=evento_id, solicitacao_id="SOL-X", paciente_id="PAC-X", data_evento=data,
                tipo_evento=tipo, resultado=resultado, descricao="Pct informa que nao deseja mais realizar a cirurgia.")
    base.update(kw)
    return Evento(**base)


def regras(achados):
    return [a.regra for a in achados]


def test_solicitacao_sem_problemas_nao_gera_achado():
    assert detectar_bloqueantes(solicitacao(), [], []) == []


def test_todo_achado_e_bloqueante():
    achados = detectar_bloqueantes(solicitacao(observacoes="PCT DESISTIU DO PROCEDIMENTO. SOLICITA RETIRADA DA FILA."), [], [])

    assert achados and all(a.bloqueante for a in achados)
    assert set(REGRAS_BLOQUEANTES) == {"PRE-20", "PRE-21", "PRE-22", "PRE-23", "PRE-24", "PRE-25"}


# --- PRE-20: duplicata ---

def test_so_a_mais_recente_e_duplicata():
    # PAC-00151: SOL-2025-00290 (K429) e SOL-2025-00348 (K42.9)
    antiga = solicitacao("SOL-2025-00290", "PAC-00151", entrada=date(2025, 9, 19), cid_principal="K429")
    nova = solicitacao("SOL-2025-00348", "PAC-00151", entrada=date(2025, 10, 19), cid_principal="K42.9")

    assert detectar_bloqueantes(antiga, [], [nova]) == []
    (achado,) = detectar_bloqueantes(nova, [], [antiga])

    assert achado.regra == "PRE-20"
    assert [m.ref for m in achado.evidencias] == ["SOL-2025-00290", "SOL-2025-00348"]
    assert "SOL-2025-00290" in achado.acao_sugerida and "2025-09-19" in achado.acao_sugerida


def test_duplicata_de_oncologico_tambem_e_detectada():
    # PAC-00307 (C73): a decisão de não suspender é do caso de uso (I-02)
    antiga = solicitacao("SOL-2026-00743", "PAC-00307", "PROC008", date(2026, 8, 9), cid_principal="C73")
    nova = solicitacao("SOL-2026-01014", "PAC-00307", "PROC008", date(2026, 10, 11), cid_principal="C73")

    assert regras(detectar_bloqueantes(nova, [], [antiga])) == ["PRE-20"]


@pytest.mark.parametrize("kw", [{"paciente": "PAC-Y"}, {"proc": "PROC999"}])
def test_outro_paciente_ou_outro_procedimento_nao_e_duplicata(kw):
    outra = solicitacao("SOL-A", entrada=date(2025, 1, 1), **kw)

    assert detectar_bloqueantes(solicitacao("SOL-B"), [], [outra]) == []


def test_mesma_data_desempata_pelo_id():
    a = solicitacao("SOL-A", entrada=date(2025, 1, 1))
    b = solicitacao("SOL-B", entrada=date(2025, 1, 1))

    assert detectar_bloqueantes(a, [], [b]) == []
    assert regras(detectar_bloqueantes(b, [], [a])) == ["PRE-20"]


def test_a_propria_solicitacao_na_lista_nao_conta():
    s = solicitacao("SOL-A")

    assert detectar_bloqueantes(s, [], [s]) == []


# --- PRE-21/22/23: saída da fila ---

def test_desistencia_nas_duas_fontes_e_pre_23():
    # SOL-2024-00076
    s = solicitacao("SOL-2024-00076", cid_principal="K40.9",
                    observacoes="PCT DESISTIU DO PROCEDIMENTO. SOLICITA RETIRADA DA FILA.")

    (achado,) = detectar_bloqueantes(s, [evento()], [])

    assert achado.regra == "PRE-23"
    assert [m.fonte for m in achado.evidencias] == ["observacoes", "evento"]


def test_desistencia_so_na_observacao():
    s = solicitacao(observacoes='Paciente refere que nao deseja mais operar no momento, "melhorou com remedio".')

    assert regras(detectar_bloqueantes(s, [], [])) == ["PRE-23"]


def test_desistencia_so_no_evento_do_call_center():
    assert regras(detectar_bloqueantes(solicitacao(), [evento()], [])) == ["PRE-23"]


def test_operou_em_outro_servico_nas_duas_fontes_e_pre_21():
    s = solicitacao(observacoes="Paciente informou por telefone que realizou a cirurgia em outro servico (GHC) em 30/06/2026.")
    e = evento(resultado="informou_cirurgia_outro_servico",
               descricao="Pct informa que ja realizou o procedimento em outro servico.")

    assert regras(detectar_bloqueantes(s, [e], [])) == ["PRE-21"]


def test_operou_pelo_convenio_so_na_observacao_e_pre_22():
    s = solicitacao(observacoes="Familiar informa que paciente operou pelo convenio.")

    (achado,) = detectar_bloqueantes(s, [], [])

    assert achado.regra == "PRE-22"
    assert "convênio" in achado.titulo


# --- PRE-25: fontes contraditórias ---

@pytest.mark.parametrize("sol_id, observacao", [
    ("SOL-2026-00305", "Familiar informa que paciente operou pelo convenio."),   # exemplo do doc
    ("SOL-2025-00453", "Familiar informa que paciente operou pelo convenio."),   # mesmo padrão nos dados
    ("SOL-2023-00054", "Paciente informou por telefone que realizou a cirurgia em outro servico (Hospital de Clinicas) em 09/09/2026."),
])
def test_call_center_diz_desistiu_e_observacao_diz_outra_coisa(sol_id, observacao):
    s = solicitacao(sol_id, observacoes=observacao)

    (achado,) = detectar_bloqueantes(s, [evento("EVT-566")], [])

    assert achado.regra == "PRE-25"
    # as duas evidências, lado a lado
    assert [(m.fonte, m.sinal) for m in achado.evidencias][1] == ("evento", "desistencia")
    assert achado.evidencias[0].fonte == "observacoes" and achado.evidencias[0].evidencia == observacao


def test_observacao_com_dois_motivos_tambem_e_contraditoria():
    s = solicitacao(observacoes="Familiar informa que paciente operou pelo convenio. PCT DESISTIU.")

    assert regras(detectar_bloqueantes(s, [], [])) == ["PRE-25"]


def test_observacao_comum_nao_e_saida():
    s = solicitacao(observacoes="Pct confirma que ainda deseja a cirurgia.")

    assert detectar_bloqueantes(s, [], []) == []


def test_evento_duplicado_ou_historico_nao_conta_como_saida():
    eventos = [evento("EVT-2", duplicado_de="EVT-1"), evento("EVT-3", historico=True)]

    assert detectar_bloqueantes(solicitacao(), eventos, []) == []


def test_outros_tipos_de_evento_nao_sao_saida():
    assert detectar_bloqueantes(solicitacao(), [evento(resultado="atendeu"), evento("E2", resultado="nao_atendeu")], []) == []


def test_duplicata_e_saida_geram_dois_achados():
    antiga = solicitacao("SOL-A", entrada=date(2025, 1, 1))
    nova = solicitacao("SOL-B", entrada=date(2025, 6, 1), observacoes="PCT DESISTIU DO PROCEDIMENTO.")

    assert regras(detectar_bloqueantes(nova, [], [antiga])) == ["PRE-20", "PRE-23"]


# --- PRE-24: evento órfão ---

def test_evento_orfao():
    # EVT-000287 -> SOL-2023-00941
    e = evento("EVT-000287", "consulta", "falta", solicitacao_id="SOL-2023-00941",
               descricao="Registro de solicitacao removida da fila.")

    achados = detectar_eventos_orfaos([e], {"SOL-2023-00001"})

    assert list(achados) == ["SOL-2023-00941"]
    achado = achados["SOL-2023-00941"]
    assert (achado.regra, achado.bloqueante) == ("PRE-24", True)
    assert achado.evidencias[0].ref == "EVT-000287"
    assert "SOL-2023-00941" in achado.acao_sugerida


def test_evento_de_solicitacao_existente_nao_e_orfao():
    assert detectar_eventos_orfaos([evento("E1")], {"SOL-X"}) == {}


def test_varios_orfaos_da_mesma_solicitacao_viram_um_achado():
    eventos = [evento("E1", solicitacao_id="SOL-Z"), evento("E2", solicitacao_id="SOL-Z"),
               evento("E3", solicitacao_id="SOL-W")]

    achados = detectar_eventos_orfaos(eventos, set())

    assert {k: len(v.evidencias) for k, v in achados.items()} == {"SOL-Z": 2, "SOL-W": 1}
