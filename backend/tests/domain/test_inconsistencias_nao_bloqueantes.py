"""PRE-10..PRE-15 (US-05): regras puras, sem banco. Textos copiados do dataset real."""
from datetime import date

import pytest

from app.domain.models import Evento, Solicitacao
from app.domain.preprocessing.inconsistencias import (
    ALERTA_POR_REGRA,
    REGRAS_COM_PENDENCIA,
    detectar_nao_bloqueantes,
)

ENTRADA = date(2025, 5, 1)
JUSTIFICATIVA = "Colelitiase sintomatica com crises de colica biliar recorrentes, USG com calculos multiplos."


def solicitacao(**kw) -> Solicitacao:
    """Uma solicitação sem nenhuma inconsistência; cada teste estraga um campo."""
    base = dict(solicitacao_id="SOL-X", paciente_id="PAC-X", procedimento_id="PROC004",
                cid_principal="K80.1", data_entrada_fila=ENTRADA, justificativa_clinica=JUSTIFICATIVA,
                observacoes="", prioridade_regulacao="media", intensidade_dor_eva=4, asa=2,
                distancia_hospital_km=20, flag_diabetico="nao", comorbidades="HAS")
    base.update(kw)
    return Solicitacao(**base)


def evento(evento_id="EVT-1", tipo="contato_telefonico", resultado="nao_atendeu", data=date(2025, 6, 1), **kw):
    base = dict(evento_id=evento_id, solicitacao_id="SOL-X", paciente_id="PAC-X", data_evento=data,
                tipo_evento=tipo, resultado=resultado, descricao="Tentativa de contato sem sucesso.")
    base.update(kw)
    return Evento(**base)


def regras(achados):
    return [a.regra for a in achados]


def test_solicitacao_sem_problemas_nao_gera_achado():
    assert detectar_nao_bloqueantes(solicitacao(), []) == []


def test_nenhum_achado_e_bloqueante():
    s = solicitacao(observacoes="PCT NAO POSSUI TELEFONE FIXO. CONTATO VIA ACS.", asa=None,
                    justificativa_clinica="Solicito cirurgia.")

    achados = detectar_nao_bloqueantes(s, [evento("E1"), evento("E2")])

    assert achados and not any(a.bloqueante for a in achados)


def test_cada_regra_tem_um_alerta():
    assert set(ALERTA_POR_REGRA) == {"PRE-10", "PRE-11", "PRE-12", "PRE-13", "PRE-14", "PRE-15"}
    assert REGRAS_COM_PENDENCIA == ("PRE-10", "PRE-11", "PRE-12", "PRE-13")  # PRE-14/15 só alertam


# --- PRE-10: contato perdido ---

def test_numero_nao_existe_e_contato_perdido():
    # SOL-2025-00053
    s = solicitacao(observacoes="NAO ATENDE. NUMERO NAO EXISTE.")

    (achado,) = detectar_nao_bloqueantes(s, [])

    assert achado.regra == "PRE-10"
    assert [m.sinal for m in achado.evidencias] == ["numero_inexistente"]


def test_duas_tentativas_sem_resposta_e_contato_perdido():
    (achado,) = detectar_nao_bloqueantes(solicitacao(), [evento("E1"), evento("E2")])

    assert achado.regra == "PRE-10"
    assert [m.ref for m in achado.evidencias] == ["E1", "E2"]


def test_uma_tentativa_so_nao_e_contato_perdido():
    assert detectar_nao_bloqueantes(solicitacao(), [evento("E1")]) == []


def test_tentativa_duplicada_ou_historica_nao_conta():
    duplicada = evento("E2", duplicado_de="E1")
    historica = evento("E3", historico=True)

    assert detectar_nao_bloqueantes(solicitacao(), [evento("E1"), duplicada, historica]) == []


def test_atendeu_nao_conta_como_tentativa_sem_resposta():
    eventos = [evento("E1"), evento("E2", resultado="atendeu")]

    assert detectar_nao_bloqueantes(solicitacao(), eventos) == []


# --- PRE-11: sem telefone ---

@pytest.mark.parametrize("observacao", [
    "PCT NAO POSSUI TELEFONE FIXO. CONTATO VIA ACS.",     # SOL-2026-00059
    "Mora em zona rural, sem telefone proprio. Contato via ACS.",
    "ACS informa que paciente mudou de endereco, sem novo contato.",
])
def test_contato_via_acs(observacao):
    assert regras(detectar_nao_bloqueantes(solicitacao(observacoes=observacao), [])) == ["PRE-11"]


def test_observacao_comum_nao_dispara_pre_11():
    assert detectar_nao_bloqueantes(solicitacao(observacoes="Familiar (filha) e o contato principal."), []) == []


# --- PRE-12: câncer escondido ---

def test_biopsia_positiva_com_cid_nao_oncologico():
    # SOL-2026-00757: D37.4 com biópsia positiva
    s = solicitacao(cid_principal="D37.4", cid_descricao="Neoplasia de comportamento incerto do colon")
    biopsia = evento("EVT-9", "biopsia", "positivo", descricao="Adenocarcinoma de colon.")

    (achado,) = detectar_nao_bloqueantes(s, [biopsia])

    assert achado.regra == "PRE-12"
    assert [m.fonte for m in achado.evidencias] == ["evento", "cid"]
    assert achado.evidencias[0].ref == "EVT-9"


def test_biopsia_positiva_com_cid_oncologico_nao_e_escondido():
    s = solicitacao(cid_principal="C18.7")

    assert detectar_nao_bloqueantes(s, [evento("EVT-9", "biopsia", "positivo")]) == []


def test_biopsia_negativa_nao_dispara():
    assert detectar_nao_bloqueantes(solicitacao(cid_principal="D37.4"),
                                    [evento("EVT-9", "biopsia", "negativo")]) == []


def test_biopsia_historica_conta():
    # a biópsia que gerou a solicitação é anterior à entrada e continua valendo
    biopsia = evento("EVT-9", "biopsia", "positivo", data=date(2025, 1, 10), historico=True)

    assert regras(detectar_nao_bloqueantes(solicitacao(cid_principal="D37.4"), [biopsia])) == ["PRE-12"]


# --- PRE-13: diabetes fora do cadastro ---

def test_diabetes_nao_consta_no_cadastro():
    # SOL-2026-00444
    s = solicitacao(observacoes="HbA1c 9,4% em 18/10/2026. Diabetes nao consta no cadastro, atualizar.",
                    comorbidades="HAS; anticoagulacao oral")

    (achado,) = detectar_nao_bloqueantes(s, [])

    assert achado.regra == "PRE-13"
    assert achado.evidencias[0].sinal == "diabetes_no_texto"


def test_hba1c_alta_em_evento_sem_diabetes_no_cadastro():
    (achado,) = detectar_nao_bloqueantes(solicitacao(), [evento("E1", "hba1c", "resultado", valor_numerico=8.7)])

    assert achado.regra == "PRE-13"
    assert achado.evidencias[0].evidencia == "HbA1c 8.7%"


def test_hba1c_do_cadastro_tambem_vale():
    assert regras(detectar_nao_bloqueantes(solicitacao(hba1c_ultima=7.4), [])) == ["PRE-13"]


def test_hba1c_normal_nao_dispara():
    assert detectar_nao_bloqueantes(solicitacao(hba1c_ultima=5.8), [evento("E1", "hba1c", "resultado", valor_numerico=6.0)]) == []


@pytest.mark.parametrize("kw", [{"flag_diabetico": "sim"}, {"comorbidades": "HAS; DM2; obesidade"}])
def test_diabetes_ja_cadastrado_nao_dispara(kw):
    s = solicitacao(hba1c_ultima=9.0, observacoes="Diabetes nao consta no cadastro, atualizar.", **kw)

    assert detectar_nao_bloqueantes(s, []) == []


# --- PRE-14: justificativa sem conteúdo ---

@pytest.mark.parametrize("texto", [
    "Solicito cirurgia.",                        # SOL-2026-00932
    "Conforme laudo anexo.",                     # SOL-2025-00375
    "Indicacao cirurgica.",
    "Solicito cirurgia. DM2 em uso de metformina.",
    "Paciente com indicacao de colectomia.",
    "",
])
def test_justificativa_generica(texto):
    assert regras(detectar_nao_bloqueantes(solicitacao(justificativa_clinica=texto), [])) == ["PRE-14"]


def test_justificativa_generica_mas_longa_passa():
    texto = "Indicacao cirurgica. Hipertensa em uso de losartana, em acompanhamento ambulatorial regular."

    assert detectar_nao_bloqueantes(solicitacao(justificativa_clinica=texto), []) == []


def test_justificativa_clinica_curta_mas_especifica_passa():
    assert detectar_nao_bloqueantes(
        solicitacao(justificativa_clinica="Cisto epidermico dorso, 3,5 cm, episodios de infeccao."), []) == []


# --- PRE-15: campo vazio ---

@pytest.mark.parametrize("campo, valor", [
    ("prioridade_regulacao", None), ("prioridade_regulacao", "  "), ("intensidade_dor_eva", None),
    ("asa", None), ("distancia_hospital_km", None),
])
def test_campo_vazio(campo, valor):
    (achado,) = detectar_nao_bloqueantes(solicitacao(**{campo: valor}), [])

    assert achado.regra == "PRE-15"
    assert achado.evidencias[0].evidencia == f"{campo} sem valor"


def test_zero_nao_e_vazio():
    assert detectar_nao_bloqueantes(solicitacao(intensidade_dor_eva=0), []) == []


def test_varios_campos_vazios_geram_um_achado_so():
    (achado,) = detectar_nao_bloqueantes(solicitacao(asa=None, intensidade_dor_eva=None), [])

    assert len(achado.evidencias) == 2
