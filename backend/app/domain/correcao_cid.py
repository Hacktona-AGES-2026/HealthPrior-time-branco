"""Correção de CID a partir de evento (PRE-12, "câncer escondido"). Funções puras.

O LLM só sugere o CID e cita o trecho do laudo; quem troca o CID é o regulador (I-05). A troca
vale para tudo que usa o CID (oncológico, SWALIS, trava), e o original continua guardado (I-10).
"""
from __future__ import annotations

import re

from app.domain.cid import is_oncologico, normalizar_cid
from app.domain.errors import ResolucaoInvalidaError
from app.domain.models import Correcao, Pendencia, Solicitacao, SugestaoCid
from app.domain.preprocessing.inconsistencias import PRE_CANCER_ESCONDIDO

# Sinal das evidências da PRE-12 que trazem o texto do laudo (ver `inconsistencias._cancer_escondido`).
SINAL_LAUDO = "biopsia_positiva"
# Citação curta demais ("ca") existe no laudo mas não sustenta CID nenhum.
MIN_CARACTERES_CITACAO = 6
_ESPACOS = re.compile(r"\s+")


def _comparavel(texto: str) -> str:
    return _ESPACOS.sub(" ", (texto or "").strip().lower())


def laudos_da_pendencia(p: Pendencia) -> list[tuple[str | None, str]]:
    """(evento_id, texto) de cada laudo citado na pendência PRE-12."""
    return [(m.ref, m.evidencia) for m in p.evidencias if m.sinal == SINAL_LAUDO and m.evidencia.strip()]


def motivo_rejeicao(sugestao: SugestaoCid, laudo: str, cid_atual: str,
                    descricao_na_tabela: str | None) -> str | None:
    """Por que a sugestão não pode ser mostrada ao regulador, ou None se ela vale.

    Vale só se o código existe na tabela CID-10, é diferente do atual e a citação está
    literalmente no laudo (I-05: o LLM cita, não inventa).
    """
    if descricao_na_tabela is None:
        return f"CID {sugestao.cid} não existe na tabela CID-10"
    if normalizar_cid(sugestao.cid) == normalizar_cid(cid_atual):
        return "o CID sugerido é o mesmo do cadastro"
    citacao = _comparavel(sugestao.citacao)
    if len(citacao) < MIN_CARACTERES_CITACAO or citacao not in _comparavel(laudo):
        return "a citação não aparece literalmente no laudo"
    return None


def aplicar_correcao_cid(s: Solicitacao, cid: str, descricao: str) -> Correcao:
    """O regulador confirmou o CID: passa a valer para tudo e devolve a correção para o log (I-10)."""
    if normalizar_cid(cid) == normalizar_cid(s.cid_principal):
        raise ResolucaoInvalidaError(f"O CID {cid} já é o CID da solicitação.")
    if is_oncologico(s.cid_principal) and not is_oncologico(cid):
        # I-02: a PRE-12 existe para achar câncer, nunca para tirar um paciente do grupo oncológico
        raise ResolucaoInvalidaError(
            f"{s.cid_principal} é oncológico: a correção pela PRE-12 não troca para um CID não oncológico.")
    original = s.cid_original or s.cid_principal
    correcao = Correcao(s.solicitacao_id, "cid_principal", s.cid_principal, cid, PRE_CANCER_ESCONDIDO)
    s.cid_original = original
    s.cid_confirmado = cid
    s.cid_principal, s.cid_descricao = cid, descricao
    s.cid_norm = normalizar_cid(cid)
    s.oncologico = is_oncologico(cid)  # I-09: sempre pelo CID
    return correcao
