"""Resolução de pendências (US-07, C-06): o que cada regra aceita e como se funde uma duplicata.

Funções puras. Quem persiste e confirma é o caso de uso `ResolverPendencia`.
"""
from __future__ import annotations

from app.domain.enums import ResolucaoPendencia as R
from app.domain.enums import StatusFila, StatusPendencia
from app.domain.errors import ObservacaoObrigatoriaError, ResolucaoInvalidaError
from app.domain.models import Correcao, Solicitacao
from app.domain.preprocessing.inconsistencias import (
    PRE_CANCER_ESCONDIDO,
    PRE_CONTATO_PERDIDO,
    PRE_DESISTENCIA,
    PRE_DIABETES_FORA_DO_CADASTRO,
    PRE_DUPLICATA,
    PRE_EVENTO_ORFAO,
    PRE_FONTES_CONTRADITORIAS,
    PRE_OPEROU_CONVENIO,
    PRE_OPEROU_FORA,
    PRE_SEM_TELEFONE,
)

_SAIDA = frozenset({R.CONFIRMAR_SAIDA, R.REATIVAR, R.DESCARTAR})
_SO_ALERTAM = frozenset({R.REATIVAR, R.DESCARTAR})  # não bloqueiam: não há saída a confirmar

# D-89: o que cada regra aceita. Duplicata funde; saída da fila confirma; evento órfão só descarta.
RESOLUCOES_POR_REGRA: dict[str, frozenset[R]] = {
    PRE_DUPLICATA: frozenset({R.FUNDIR, R.REATIVAR, R.DESCARTAR}),
    PRE_OPEROU_FORA: _SAIDA,
    PRE_OPEROU_CONVENIO: _SAIDA,
    PRE_DESISTENCIA: _SAIDA,
    PRE_FONTES_CONTRADITORIAS: _SAIDA,
    PRE_EVENTO_ORFAO: frozenset({R.DESCARTAR}),
    PRE_CONTATO_PERDIDO: _SO_ALERTAM,
    PRE_SEM_TELEFONE: _SO_ALERTAM,
    PRE_CANCER_ESCONDIDO: _SO_ALERTAM,
    PRE_DIABETES_FORA_DO_CADASTRO: _SO_ALERTAM,
}

# `descartar` é a única que termina como "descartada"; as demais, "resolvida".
STATUS_DA_PENDENCIA: dict[R, StatusPendencia] = {
    R.CONFIRMAR_SAIDA: StatusPendencia.RESOLVIDA,
    R.FUNDIR: StatusPendencia.RESOLVIDA,
    R.REATIVAR: StatusPendencia.RESOLVIDA,
    R.DESCARTAR: StatusPendencia.DESCARTADA,
}


def validar_resolucao(regra: str, resolucao: R, observacao: str | None) -> None:
    aceitas = RESOLUCOES_POR_REGRA.get(regra, frozenset())
    if resolucao not in aceitas:
        opcoes = ", ".join(sorted(r.value for r in aceitas)) or "nenhuma"
        raise ResolucaoInvalidaError(f"A regra {regra} não aceita \"{resolucao.value}\". Aceita: {opcoes}.")
    if resolucao == R.CONFIRMAR_SAIDA and not (observacao or "").strip():  # D-90
        raise ObservacaoObrigatoriaError("Confirmar a saída exige uma observação com o motivo.")


def fundir(permanece: Solicitacao, removida: Solicitacao) -> list[Correcao]:
    """PRE-20 (D-10, D-91): `removida` sai da fila e `permanece` fica com a data de entrada mais antiga.

    Devolve as correções feitas em dado original (I-10). Os eventos são movidos pelo caso de uso.
    """
    if permanece.solicitacao_id == removida.solicitacao_id:
        raise ResolucaoInvalidaError("Não dá para fundir uma solicitação com ela mesma.")
    if (permanece.paciente_id, permanece.procedimento_id) != (removida.paciente_id, removida.procedimento_id):
        raise ResolucaoInvalidaError("Só se fundem solicitações do mesmo paciente e procedimento.")
    if permanece.status_fila == StatusFila.REMOVIDA:
        raise ResolucaoInvalidaError(f"{permanece.solicitacao_id} já foi removida e não pode permanecer.")

    correcoes: list[Correcao] = []
    mais_antiga = min(permanece.data_entrada_fila, removida.data_entrada_fila)
    if mais_antiga != permanece.data_entrada_fila:
        correcoes.append(Correcao(permanece.solicitacao_id, "data_entrada_fila",
                                  permanece.data_entrada_fila.isoformat(), mais_antiga.isoformat(), PRE_DUPLICATA))
        permanece.data_entrada_fila = mais_antiga
    removida.status_fila, removida.motivo_status = StatusFila.REMOVIDA, PRE_DUPLICATA
    return correcoes
