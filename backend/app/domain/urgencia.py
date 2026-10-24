"""Sinais de urgência clínica usados para a camada 2 (C-11).

A camada 2 deve ser pelo menos tão abrangente quanto o complemento de "sem urgência"
do verificador oficial (src/verificar_fila_priorizada.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Mesma lista do verificador oficial. Mantenha sincronizado.
_KW_ALARME = re.compile(
    r"encarcer|estrangul|colangite|icter|pancreatite|enterorragia|melena|hematemese|suboclus|"
    r"perda ponderal|disfagia|sepse|hidronefrose|perda de funcao|transfund|hemoptise|rouquidao|"
    r"linfonodo.*(?:fixo|palpavel)|sangramento espontaneo|acamad|ulcera de pressao|"
    r"quedas de repeticao|glaucoma facomorfico|retencao de co2|dano neurologico|psa em elevacao|"
    r"dessaturacao|angina em repouso|sincope|crescimento rapido|retencao urinaria aguda|"
    r"massa anexial|ca-125"
)

EVENTOS_DE_PIORA = {
    ("pronto_socorro", None),
    ("internacao", None),
    ("biopsia", "positivo"),
    ("exame_imagem", "progressao"),
    ("consulta_reavaliacao", "piora"),
}


@dataclass
class SinaisUrgencia:
    cid_norm: str
    intensidade_dor_eva: int | None
    limitacao_funcional: str | None
    tem_evento_de_piora: bool  # durante a espera, sem duplicados/histórico
    justificativa_clinica: str


def tem_sinal_alarme(texto: str | None) -> bool:
    return bool(texto) and bool(_KW_ALARME.search(texto.lower()))


def evento_e_piora(tipo_evento: str, resultado: str | None) -> bool:
    return (tipo_evento, None) in EVENTOS_DE_PIORA or (tipo_evento, resultado) in EVENTOS_DE_PIORA


def is_urgente(sinais: SinaisUrgencia) -> bool:
    """TODO(US-08): urgente não oncológico = NÃO 'sem urgência' do verificador."""
    raise NotImplementedError("US-08: is_urgente")
