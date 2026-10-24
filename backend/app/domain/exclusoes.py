"""US-11 · Quem ficou fora da fila e por quê (tabela do DECISOES.md).

Funções puras. Uma solicitação fica fora da fila quando não está `ativa`: `suspensa` (achado bloqueante
aguardando confirmação, D-71) ou `removida` (saída confirmada ou duplicata fundida, D-82/D-83). O motivo
é a regra PRE-xx gravada em `motivo_status`.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import StatusFila
from app.domain.models import Solicitacao
from app.domain.preprocessing.inconsistencias import (
    PRE_DESISTENCIA,
    PRE_DUPLICATA,
    PRE_FONTES_CONTRADITORIAS,
    PRE_OPEROU_CONVENIO,
    PRE_OPEROU_FORA,
)

NOMES_REGRA: dict[str, str] = {
    PRE_DUPLICATA: "Duplicata",
    PRE_OPEROU_FORA: "Operou em outro serviço",
    PRE_OPEROU_CONVENIO: "Operou pelo convênio",
    PRE_DESISTENCIA: "Desistência",
    PRE_FONTES_CONTRADITORIAS: "Fontes contraditórias",
}
SEM_MOTIVO = "sem motivo registrado"

CABECALHO = "| Motivo (regra) | Quantidade | Solicitações | Observação |\n|---|---|---|---|"


@dataclass(frozen=True)
class GrupoExclusao:
    regra: str
    ids: tuple[str, ...]
    suspensas: int
    removidas: int
    oncologicas: tuple[str, ...]  # fora da fila e oncológicas: o verificador pede justificativa (I-02)

    @property
    def quantidade(self) -> int:
        return len(self.ids)

    @property
    def motivo(self) -> str:
        nome = NOMES_REGRA.get(self.regra)
        return f"{nome} ({self.regra})" if nome else self.regra


def agrupar_exclusoes(solicitacoes: list[Solicitacao]) -> list[GrupoExclusao]:
    """Agrupa por regra as solicitações que não estão ativas; ordena por regra e por id."""
    por_regra: dict[str, list[Solicitacao]] = {}
    for s in solicitacoes:
        if s.status_fila != StatusFila.ATIVA:
            por_regra.setdefault(s.motivo_status or SEM_MOTIVO, []).append(s)
    grupos = []
    for regra in sorted(por_regra):
        membros = sorted(por_regra[regra], key=lambda s: s.solicitacao_id)
        grupos.append(GrupoExclusao(
            regra=regra,
            ids=tuple(s.solicitacao_id for s in membros),
            suspensas=sum(s.status_fila == StatusFila.SUSPENSA for s in membros),
            removidas=sum(s.status_fila == StatusFila.REMOVIDA for s in membros),
            oncologicas=tuple(s.solicitacao_id for s in membros if s.oncologico),
        ))
    return grupos


def _observacao(g: GrupoExclusao) -> str:
    partes = []
    if g.removidas:
        partes.append(f"{g.removidas} removida{'s' if g.removidas > 1 else ''} (saída confirmada por uma pessoa)")
    if g.suspensas:
        plural = g.suspensas > 1
        partes.append(f"{g.suspensas} suspensa{'s' if plural else ''} (até uma pessoa confirmar a saída; "
                      f"{'voltam' if plural else 'volta'} à fila se reativada{'s' if plural else ''})")
    if g.oncologicas:
        partes.append(f"oncológica{'s' if len(g.oncologicas) > 1 else ''}: {', '.join(g.oncologicas)}")
    return "; ".join(partes)


def tabela_markdown(grupos: list[GrupoExclusao]) -> str:
    if not grupos:
        return f"{CABECALHO}\n| Nenhuma | 0 | | Todas as solicitações estão na fila |"
    linhas = [f"| {g.motivo} | {g.quantidade} | {', '.join(g.ids)} | {_observacao(g)} |" for g in grupos]
    return "\n".join([CABECALHO, *linhas])


TITULO_SECAO = "## Solicitações fora da fila"


def substituir_secao(texto: str, conteudo: str) -> str:
    """Troca o corpo da seção "Solicitações fora da fila" (até o próximo `## `) por `conteudo`."""
    inicio = texto.find(TITULO_SECAO)
    if inicio < 0:
        raise ValueError(f'O documento não tem a seção "{TITULO_SECAO}"')
    corpo_ini = inicio + len(TITULO_SECAO)
    fim = texto.find("\n## ", corpo_ini)
    resto = texto[fim:] if fim >= 0 else ""
    return f"{texto[:corpo_ini]}\n\n{conteudo.strip()}\n{resto}"
