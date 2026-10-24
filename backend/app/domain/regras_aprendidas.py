"""US-19 · Regras aprendidas (C-14): o que o comitê aprova e como entra no SWALIS. Funções puras.

Uma regra aprovada é `procedimento + classe_de → classe_para`: se o procedimento bate e a classe que o
SWALIS calculou é `classe_de`, a sugerida vira `classe_para`. Não mexe na fórmula de prazo nem em quem está
confirmado; a nova sugerida passa pelo regulador como qualquer outra mudança de classe (I-04, C-08).
Rebaixar nunca vale para oncológico (I-01).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.aprendizado import direcao
from app.domain.cid import is_oncologico
from app.domain.enums import Classe
from app.domain.models import Solicitacao


@dataclass(frozen=True)
class RegraAprendida:
    regra_id: str  # o `proposta_id` que a originou
    procedimento_id: str
    classe_de: Classe
    classe_para: Classe
    versao: int  # N da versão de regras em que entrou


@dataclass(frozen=True)
class RegraRegistrada:
    """A regra com o histórico de quem aprovou e, se foi o caso, de quem reverteu e por quê."""

    regra: RegraAprendida
    ativa: bool
    aprovada_por: str
    revertida_por: str | None = None
    revertida_em: datetime | None = None
    motivo_reversao: str | None = None


def _oncologica(s: Solicitacao) -> bool:
    return is_oncologico(s.cid_norm or s.cid_principal)


def aplicar_regras(s: Solicitacao, classe_base: Classe,
                   regras: list[RegraAprendida]) -> tuple[Classe, RegraAprendida | None]:
    """Devolve a classe depois das regras e a regra que mudou (a de maior versão, se houver mais de uma)."""
    candidatas = [r for r in regras if r.procedimento_id == s.procedimento_id and r.classe_de == classe_base]
    for r in sorted(candidatas, key=lambda r: -r.versao):
        if direcao(r.classe_de, r.classe_para) == "rebaixar" and _oncologica(s):
            continue  # I-01
        return r.classe_para, r
    return classe_base, None


def versao_atual(regras: list[RegraAprendida]) -> int:
    return max((r.versao for r in regras), default=0)


@dataclass
class Impacto:
    """Shadow run: o que a regra nova mudaria na fila de hoje, sem aplicar nada."""

    afetados: int = 0
    oncologicos_afetados: int = 0
    oncologicos_rebaixados: int = 0  # tem de ser 0 (I-01)
    exemplos: list[str] = field(default_factory=list)  # solicitacao_id, até 10
    ids: list[str] = field(default_factory=list)  # todos os afetados


def simular_impacto(candidatas: list[tuple[Solicitacao, Classe]], regra: RegraAprendida) -> Impacto:
    """`candidatas`: solicitações ativas com a classe que o SWALIS dá hoje (já com as regras em vigor)."""
    imp = Impacto()
    for s, classe in candidatas:
        nova, aplicada = aplicar_regras(s, classe, [regra])
        if aplicada is None:
            continue
        imp.afetados += 1
        imp.ids.append(s.solicitacao_id)
        if _oncologica(s):
            imp.oncologicos_afetados += 1
            if direcao(classe, nova) == "rebaixar":
                imp.oncologicos_rebaixados += 1
    imp.exemplos = sorted(imp.ids)[:10]
    return imp
