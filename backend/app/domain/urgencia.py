"""Sinais usados pela trava (C-11).

- Sinais clínicos (`motivos_urgencia`) definem a camada 2: algo indica que o risco de
  esperar aumentou (complicação, piora durante a espera, biópsia positiva, alarme no texto).
- Sintomas (`motivos_sintomas`: dor > 3, limitação moderada/grave) NÃO definem camada (D-27):
  aparecem na justificativa e são critério do SWALIS para a classe (B/C/D).

A regra de ouro depende de uma inclusão (D-112): a camada 2 divide o bloco prioritário com os
oncológicos e pode passar um deles, então todo sinal daqui tem que ser também urgência para o
verificador oficial (`src/verificar_fila_priorizada.py`): mesmos CIDs, termos de alarme e tipos
de evento de piora. Não acrescente sinal que o verificador não conheça.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.domain.cid import is_cid_urgente
from app.domain.models import Evento

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
    tem_evento_de_piora: bool
    justificativa_clinica: str
    tem_biopsia_positiva: bool = False


def tem_sinal_alarme(texto: str | None) -> bool:
    return bool(texto and _KW_ALARME.search(texto.lower()))


def evento_e_piora(tipo_evento: str, resultado: str | None) -> bool:
    return (tipo_evento, None) in EVENTOS_DE_PIORA or (tipo_evento, resultado) in EVENTOS_DE_PIORA


def tem_evento_de_piora_na_espera(eventos: list[Evento], data_entrada_fila: date) -> bool:
    """Indica piora clínica ocorrida enquanto o paciente já estava na fila.

    Eventos anteriores à entrada na fila são histórico e não contam. Eventos
    marcados como duplicados também são ignorados.
    """
    return any(
        evento_e_piora(e.tipo_evento, e.resultado)
        and e.data_evento >= data_entrada_fila
        and e.duplicado_de is None
        for e in eventos
    )


def tem_biopsia_positiva(eventos: list[Evento]) -> bool:
    """Indica biópsia positiva em qualquer data, inclusive antes da entrada na fila.

    Cobre o câncer escondido: biópsia positiva com CID que não começa com C.
    """
    return any(e.tipo_evento == "biopsia" and e.resultado == "positivo" for e in eventos)


def motivos_urgencia(sinais: SinaisUrgencia) -> list[str]:
    """Códigos dos sinais clínicos de urgência (camada 2), sem repetição e em ordem fixa.

    Ordem: cid_complicacao, evento_piora, biopsia_positiva, sinal_alarme.
    Dor e limitação ficam em `motivos_sintomas` (D-27, revisa D-22).
    """
    motivos: list[str] = []
    if is_cid_urgente(sinais.cid_norm):
        motivos.append("cid_complicacao")
    if sinais.tem_evento_de_piora:
        motivos.append("evento_piora")
    if sinais.tem_biopsia_positiva:
        motivos.append("biopsia_positiva")
    if tem_sinal_alarme(sinais.justificativa_clinica):
        motivos.append("sinal_alarme")
    return motivos


def motivos_sintomas(sinais: SinaisUrgencia) -> list[str]:
    """Sintomas relevantes (dor > 3, limitação moderada/grave). Não definem camada (D-27).

    Usados na justificativa; a intensidade do sintoma é critério do SWALIS (classe B/C/D).
    """
    sintomas: list[str] = []
    if (sinais.intensidade_dor_eva or 0) > 3:
        sintomas.append("dor")
    if (sinais.limitacao_funcional or "nenhuma") not in ("nenhuma", "leve"):
        sintomas.append("limitacao")
    return sintomas


def is_urgente(sinais: SinaisUrgencia) -> bool:
    """Indica se o paciente tem pelo menos um sinal clínico de urgência (camada 2)."""
    return bool(motivos_urgencia(sinais))
