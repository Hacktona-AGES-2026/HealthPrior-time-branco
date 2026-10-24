from __future__ import annotations

from datetime import date

from app.domain.models import Evento
from app.domain.urgencia import (
    SinaisUrgencia,
    is_urgente,
    motivos_sintomas,
    motivos_urgencia,
    tem_biopsia_positiva,
    tem_evento_de_piora_na_espera,
    tem_sinal_alarme,
    tem_sinal_alarme_nao_negado,
)

ENTRADA = date(2025, 1, 1)


def sinais(**kwargs) -> SinaisUrgencia:
    base = dict(
        cid_norm="K409",
        intensidade_dor_eva=2,
        limitacao_funcional="leve",
        tem_evento_de_piora=False,
        justificativa_clinica="paciente com quadro estavel",
    )
    base.update(kwargs)
    return SinaisUrgencia(**base)


def evento(
    tipo: str,
    data_evento: date,
    resultado: str | None = None,
    duplicado_de: str | None = None,
) -> Evento:
    return Evento(
        evento_id=f"EV-{tipo}-{data_evento.isoformat()}",
        solicitacao_id="SOL-1",
        paciente_id="PAC-1",
        data_evento=data_evento,
        tipo_evento=tipo,
        resultado=resultado,
        duplicado_de=duplicado_de,
    )


def test_sem_nenhum_sinal_nao_e_urgente():
    s = sinais()

    assert is_urgente(s) is False
    assert motivos_urgencia(s) == []


def test_dor_acima_de_3_e_sintoma_nao_urgencia():
    # D-27: dor sozinha não coloca na camada 2.
    s = sinais(intensidade_dor_eva=4)
    assert motivos_urgencia(s) == []
    assert is_urgente(s) is False
    assert motivos_sintomas(s) == ["dor"]


def test_limitacao_moderada_e_sintoma_nao_urgencia():
    s = sinais(limitacao_funcional="moderada")
    assert motivos_urgencia(s) == []
    assert motivos_sintomas(s) == ["limitacao"]


def test_dor_3_e_limitacao_leve_nao_sao_sintomas():
    assert motivos_sintomas(sinais(intensidade_dor_eva=3, limitacao_funcional="leve")) == []


def test_limitacao_e_dor_none_nao_sao_urgentes():
    s = sinais(limitacao_funcional=None, intensidade_dor_eva=None)

    assert is_urgente(s) is False
    assert motivos_urgencia(s) == []


def test_cid_urgente_gera_cid_complicacao():
    assert "cid_complicacao" in motivos_urgencia(sinais(cid_norm="K403"))


def test_texto_com_colangite_gera_sinal_alarme():
    s = sinais(justificativa_clinica="paciente com episodio de colangite")

    assert "sinal_alarme" in motivos_urgencia(s)


def test_alarme_negado_nao_gera_sinal_alarme():
    s = sinais(justificativa_clinica="Hernia inguinal redutivel, abaulamento aos esforcos. Sem sinais de encarceramento.")

    assert "sinal_alarme" not in motivos_urgencia(s)
    assert is_urgente(s) is False


def test_alarme_afirmado_depois_de_negacao_continua_valendo():
    s = sinais(justificativa_clinica="Sem sinais de encarceramento ontem, mas hoje com encarceramento da hernia")

    assert "sinal_alarme" in motivos_urgencia(s)


def test_um_alarme_negado_e_outro_afirmado_geram_alarme():
    s = sinais(justificativa_clinica="Sem sinais de encarceramento. Icterica ha dois dias.")

    assert "sinal_alarme" in motivos_urgencia(s)


def test_tem_sinal_alarme_segue_o_verificador_e_ignora_negacao():
    texto = "Sem sinais de encarceramento."

    assert tem_sinal_alarme(texto) is True
    assert tem_sinal_alarme_nao_negado(texto) is False


def test_evento_de_piora_depois_da_entrada_conta():
    eventos = [evento("pronto_socorro", date(2025, 2, 1))]

    assert tem_evento_de_piora_na_espera(eventos, ENTRADA) is True


def test_evento_de_piora_antes_da_entrada_nao_conta():
    eventos = [evento("pronto_socorro", date(2024, 12, 1))]

    assert tem_evento_de_piora_na_espera(eventos, ENTRADA) is False


def test_evento_de_piora_duplicado_nao_conta():
    eventos = [evento("pronto_socorro", date(2025, 2, 1), duplicado_de="EV-original")]

    assert tem_evento_de_piora_na_espera(eventos, ENTRADA) is False


def test_exame_imagem_estavel_nao_e_piora():
    eventos = [evento("exame_imagem", date(2025, 2, 1), resultado="estavel")]

    assert tem_evento_de_piora_na_espera(eventos, ENTRADA) is False


def test_exame_imagem_progressao_e_piora():
    eventos = [evento("exame_imagem", date(2025, 2, 1), resultado="progressao")]

    assert tem_evento_de_piora_na_espera(eventos, ENTRADA) is True


def test_biopsia_positiva_antes_da_entrada_conta():
    eventos = [evento("biopsia", date(2024, 11, 1), resultado="positivo")]

    assert tem_biopsia_positiva(eventos) is True


def test_biopsia_negativa_nao_conta():
    eventos = [evento("biopsia", date(2024, 11, 1), resultado="negativo")]

    assert tem_biopsia_positiva(eventos) is False


def test_biopsia_positiva_gera_motivo_biopsia_positiva():
    s = sinais(tem_biopsia_positiva=True)

    assert "biopsia_positiva" in motivos_urgencia(s)
    assert is_urgente(s) is True


def test_motivos_nao_se_repetem_e_seguem_ordem_fixa():
    s = sinais(
        cid_norm="K403",
        intensidade_dor_eva=9,
        limitacao_funcional="grave",
        tem_evento_de_piora=True,
        tem_biopsia_positiva=True,
        justificativa_clinica="sepse em curso",
    )

    assert motivos_urgencia(s) == [
        "cid_complicacao",
        "evento_piora",
        "biopsia_positiva",
        "sinal_alarme",
    ]
