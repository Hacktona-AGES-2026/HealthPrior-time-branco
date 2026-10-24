"""PRE-05..PRE-08 (US-03): regras puras, sem banco."""
from datetime import date

import pytest

from app.domain.models import Correcao, Evento, Solicitacao
from app.domain.preprocessing.flags import (
    evento_indica_piora,
    marcar_eventos,
    recalcular_flags,
)

ENTRADA = date(2023, 3, 23)


def solicitacao(cid="K40.9", flag_oncologico="nao", flag_piora="nao", sol_id="SOL-2023-00017"):
    return Solicitacao(solicitacao_id=sol_id, paciente_id="PAC-1", procedimento_id="PROC002",
                       cid_principal=cid, data_entrada_fila=ENTRADA,
                       flag_oncologico=flag_oncologico, flag_piora_clinica=flag_piora)


def evento(evento_id="EVT-1", data=date(2023, 5, 2), tipo="falta", resultado="consulta", **kw):
    base = dict(evento_id=evento_id, solicitacao_id="SOL-2023-00017", paciente_id="PAC-1",
                data_evento=data, tipo_evento=tipo, resultado=resultado,
                descricao="Paciente nao compareceu.", origem="ambulatorio")
    base.update(kw)
    return Evento(**base)


# --- PRE-05: oncológico pelo CID, nunca pela flag ---

def test_c61_com_flag_nao_vira_oncologico_e_registra_correcao():
    # SOL-2025-00149
    s = solicitacao(cid="C61", flag_oncologico="nao")

    correcoes = recalcular_flags(s, [])

    assert s.oncologico is True
    assert correcoes == [Correcao(s.solicitacao_id, "flag_oncologico", "nao", "sim", "PRE-05")]


def test_hernia_com_flag_sim_deixa_de_ser_oncologica():
    # SOL-2026-00583
    s = solicitacao(cid="K40.9", flag_oncologico="sim")

    correcoes = recalcular_flags(s, [])

    assert s.oncologico is False
    assert correcoes == [Correcao(s.solicitacao_id, "flag_oncologico", "sim", "nao", "PRE-05")]


def test_neoplasia_benigna_nao_e_oncologica():
    # SOL-2025-00196: D24 com flag "sim"
    s = solicitacao(cid="D24", flag_oncologico="sim")

    recalcular_flags(s, [])

    assert s.oncologico is False


def test_flag_oncologica_certa_nao_gera_correcao():
    s = solicitacao(cid="C18.7", flag_oncologico="sim")

    assert recalcular_flags(s, []) == []
    assert s.oncologico is True


def test_cid_sem_ponto_e_minusculo_tambem_e_oncologico():
    s = solicitacao(cid="c169", flag_oncologico="sim")

    recalcular_flags(s, [])

    assert s.oncologico is True


def test_flag_original_nunca_e_sobrescrita():
    s = solicitacao(cid="C61", flag_oncologico="nao", flag_piora="nao")

    recalcular_flags(s, [evento(tipo="pronto_socorro", resultado="observacao")])

    assert (s.flag_oncologico, s.flag_piora_clinica) == ("nao", "nao")


# --- PRE-06: piora recalculada a partir dos eventos ---

@pytest.mark.parametrize(
    "tipo, resultado, esperado",
    [("pronto_socorro", "atendido_liberado", True), ("pronto_socorro", "observacao", True),
     ("internacao", "alta", True), ("exame_imagem", "progressao", True),
     ("consulta_reavaliacao", "piora", True), ("contato_telefonico", "relata_piora", True),
     ("exame_imagem", "estavel", False), ("consulta_reavaliacao", "melhora", False),
     ("contato_telefonico", "relata_melhora", False), ("contato_telefonico", "nao_atendeu", False),
     ("biopsia", "positivo", False), ("hba1c", "resultado", False), ("falta", "consulta", False)],
)
def test_evento_indica_piora(tipo, resultado, esperado):
    assert evento_indica_piora(evento(tipo=tipo, resultado=resultado)) is esperado


def test_evento_de_piora_corrige_flag_nao_para_sim():
    s = solicitacao(flag_piora="nao")

    correcoes = recalcular_flags(s, [evento(tipo="pronto_socorro", resultado="observacao")])

    assert s.piora_recalculada is True
    assert correcoes == [Correcao(s.solicitacao_id, "flag_piora_clinica", "nao", "sim", "PRE-06")]


def test_flag_sim_sem_evento_e_mantida_sem_correcao():
    # D-19: a piora pode estar só no texto (ex.: SOL-2026-00637); não rebaixa sem evidência
    s = solicitacao(flag_piora="sim")

    assert recalcular_flags(s, []) == []
    assert s.piora_recalculada is True


def test_sem_evento_e_flag_nao_continua_sem_piora():
    s = solicitacao(flag_piora="nao")

    assert recalcular_flags(s, [evento()]) == []
    assert s.piora_recalculada is False


def test_ps_historico_nao_conta_como_piora():
    # SOL-2023-00017: 2 PS em dez/2022, antes de entrar na fila
    s = solicitacao(flag_piora="nao")
    ps = [evento("EVT-9", date(2022, 12, 16), "pronto_socorro", "atendido_liberado", descricao="a"),
          evento("EVT-10", date(2022, 12, 29), "pronto_socorro", "atendido_liberado", descricao="b")]

    marcar_eventos(s, ps)
    recalcular_flags(s, ps)

    assert s.piora_recalculada is False


def test_copia_de_evento_de_piora_nao_conta_sozinha():
    s = solicitacao(flag_piora="nao")
    original = evento("EVT-1", tipo="pronto_socorro", resultado="observacao")
    copia = evento("EVT-2", tipo="pronto_socorro", resultado="observacao")

    marcar_eventos(s, [original, copia])

    assert copia.duplicado_de == "EVT-1"
    recalcular_flags(s, [copia])  # só a cópia: não conta
    assert s.piora_recalculada is False


# --- PRE-07: evento duplicado ---

def test_duplicata_mantem_o_menor_evento_id():
    # EVT-000050 / EVT-000051 (SOL-2023-00083)
    s = solicitacao(sol_id="SOL-2023-00083")
    eventos = [evento("EVT-000051"), evento("EVT-000050")]

    marcar_eventos(s, eventos)

    por_id = {e.evento_id: e for e in eventos}
    assert por_id["EVT-000050"].duplicado_de is None
    assert por_id["EVT-000051"].duplicado_de == "EVT-000050"


def test_tres_copias_apontam_para_a_primeira():
    eventos = [evento("EVT-3"), evento("EVT-1"), evento("EVT-2")]

    marcar_eventos(solicitacao(), eventos)

    assert {e.evento_id: e.duplicado_de for e in eventos} == {"EVT-1": None, "EVT-2": "EVT-1", "EVT-3": "EVT-1"}


@pytest.mark.parametrize(
    "diferenca",
    [{"origem": "UPA Zona Norte"}, {"descricao": "Caixa postal."}, {"data": date(2023, 5, 3)},
     {"resultado": "exame"}, {"valor_numerico": 7.0}],
)
def test_eventos_com_conteudo_diferente_nao_sao_duplicata(diferenca):
    # inclui a origem: EVT-000712/713 (PS São Lucas × UPA) podem ser dois atendimentos reais
    eventos = [evento("EVT-1"), evento("EVT-2", **diferenca)]

    marcar_eventos(solicitacao(), eventos)

    assert [e.duplicado_de for e in eventos] == [None, None]


def test_marcar_eventos_e_idempotente():
    eventos = [evento("EVT-1"), evento("EVT-2")]
    s = solicitacao()

    marcar_eventos(s, eventos)
    marcar_eventos(s, eventos)

    assert [e.duplicado_de for e in eventos] == [None, "EVT-1"]


# --- PRE-08: evento anterior à entrada ---

def test_historico_antes_no_dia_e_depois_da_entrada():
    s = solicitacao()
    antes = evento("EVT-1", date(2022, 12, 16), "pronto_socorro", "atendido_liberado")
    no_dia = evento("EVT-2", ENTRADA, "contato_telefonico", "atendeu", descricao="b")
    depois = evento("EVT-3", date(2023, 8, 13), "contato_telefonico", "relata_melhora", descricao="c")

    marcar_eventos(s, [antes, no_dia, depois])

    assert (antes.historico, no_dia.historico, depois.historico) == (True, False, False)


def test_nenhum_evento_e_apagado():
    eventos = [evento("EVT-1"), evento("EVT-2")]

    assert len(marcar_eventos(solicitacao(), eventos)) == 2
