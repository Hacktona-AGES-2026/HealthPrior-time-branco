"""PRE-05..PRE-08 (US-03): flags recalculadas e eventos limpos.

Funções puras: sem banco, sem relógio. Os valores originais (`flag_oncologico`,
`flag_piora_clinica`) nunca são alterados; o valor recalculado vai para `oncologico` e
`piora_recalculada`, e cada flag original que diverge vira uma `Correcao` (I-10).

Ordem de uso por solicitação: `marcar_eventos` primeiro, depois `recalcular_flags`
(a piora só considera evento durante a espera e que não seja cópia de outro).
"""
from __future__ import annotations

from app.domain.cid import is_oncologico
from app.domain.models import Correcao, Evento, Solicitacao

PRE_ONCOLOGICO = "PRE-05"
PRE_PIORA = "PRE-06"
REGRAS_FLAGS = (PRE_ONCOLOGICO, PRE_PIORA)

# PRE-06 (D-18): eventos durante a espera que indicam piora clínica.
TIPOS_PIORA: frozenset[str] = frozenset({"pronto_socorro", "internacao"})
RESULTADOS_PIORA: frozenset[tuple[str, str]] = frozenset({
    ("exame_imagem", "progressao"),
    ("consulta_reavaliacao", "piora"),
    ("contato_telefonico", "relata_piora"),
})


def evento_indica_piora(evento: Evento) -> bool:
    return evento.tipo_evento in TIPOS_PIORA or (evento.tipo_evento, evento.resultado) in RESULTADOS_PIORA


def is_historico(evento: Evento, solicitacao: Solicitacao) -> bool:
    """PRE-08: anterior à entrada na fila. No dia da entrada já é espera (D-21)."""
    return evento.data_evento < solicitacao.data_entrada_fila


def marcar_eventos(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Evento]:
    """PRE-07 e PRE-08. Marca (sem apagar) os eventos desta solicitação e os devolve.

    Duplicado (D-20): mesmo conteúdo em tudo menos o `evento_id`, origem inclusive. Fica o de
    menor `evento_id`; os outros recebem `duplicado_de`.
    """
    primeiro_por_conteudo: dict[tuple, str] = {}
    for e in sorted(eventos, key=lambda x: x.evento_id):
        conteudo = (e.data_evento, e.tipo_evento, e.resultado, e.valor_numerico, e.descricao, e.origem)
        e.duplicado_de = primeiro_por_conteudo.setdefault(conteudo, e.evento_id)
        if e.duplicado_de == e.evento_id:
            e.duplicado_de = None
        e.historico = is_historico(e, solicitacao)
    return eventos


def recalcular_flags(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Correcao]:
    """PRE-05 (oncológico pelo CID) e PRE-06 (piora pelos eventos).

    `eventos` são os desta solicitação, já passados por `marcar_eventos`. Atualiza a
    solicitação e devolve só as correções em que a flag original estava errada.
    """
    correcoes: list[Correcao] = []

    solicitacao.oncologico = is_oncologico(solicitacao.cid_principal)
    _registrar(correcoes, solicitacao, "flag_oncologico", solicitacao.flag_oncologico,
               solicitacao.oncologico, PRE_ONCOLOGICO)

    piora_por_evento = any(
        evento_indica_piora(e) for e in eventos if not e.historico and e.duplicado_de is None
    )
    # D-19: um "sim" manual sem evento fica (a piora pode estar só no texto): só corrige "nao" -> "sim".
    solicitacao.piora_recalculada = piora_por_evento or solicitacao.flag_piora_clinica == "sim"
    _registrar(correcoes, solicitacao, "flag_piora_clinica", solicitacao.flag_piora_clinica,
               solicitacao.piora_recalculada, PRE_PIORA)
    return correcoes


def _registrar(correcoes: list[Correcao], s: Solicitacao, campo: str, original: str | None,
               recalculado: bool, regra: str) -> None:
    novo = "sim" if recalculado else "nao"
    if original and original != novo:
        correcoes.append(Correcao(s.solicitacao_id, campo, original, novo, regra))
