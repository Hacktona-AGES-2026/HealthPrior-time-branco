"""Ciclo de aprendizado (C-14, US-18): agrupa justificativas de reguladores em propostas de regra.

Puro: sem I/O. Quem monta os casos e persiste as propostas é a camada de aplicação.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.domain.enums import Classe, MotivoCodificado

ORDEM_GRAVIDADE = [Classe.A1, Classe.A2, Classe.B, Classe.C, Classe.D]  # menor índice = mais grave


@dataclass(frozen=True)
class ParametrosAprendizado:
    min_casos: int = 5
    min_reguladores: int = 3
    janela_dias: int = 90
    min_consistencia: float = 0.8


@dataclass(frozen=True)
class CasoAprendizado:
    decisao_id: str
    solicitacao_id: str
    regulador_id: str
    data: datetime
    procedimento_id: str
    motivo: MotivoCodificado
    classe_de: Classe
    classe_para: Classe
    justificativa: str | None = None
    reclassificado_por_llm: bool = False


@dataclass
class PropostaRegra:
    proposta_id: str
    procedimento_id: str
    motivo: MotivoCodificado
    classe_de: Classe
    classe_para: Classe
    direcao: str  # "subir" | "rebaixar"
    n_casos: int
    n_reguladores: int
    consistencia: float
    casos: list[str] = field(default_factory=list)
    status: str = "pendente"  # "pendente" | "descartada" | "aprovada" | "rejeitada"
    motivo_descarte: str | None = None
    decidida_por: str | None = None  # US-19
    decidida_em: datetime | None = None
    observacao: str | None = None


def direcao(de: Classe, para: Classe) -> str | None:
    i_de, i_para = ORDEM_GRAVIDADE.index(de), ORDEM_GRAVIDADE.index(para)
    if i_de == i_para:
        return None
    return "subir" if i_para < i_de else "rebaixar"


def proposta_id(procedimento_id: str, motivo: MotivoCodificado, de: Classe, para: Classe) -> str:
    return f"PROP-{procedimento_id}-{_v(motivo)}-{_v(de)}-{_v(para)}"


def _v(x) -> str:
    return x.value if hasattr(x, "value") else str(x)


def _utc(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def agrupar(casos: list[CasoAprendizado], referencia: datetime, params: ParametrosAprendizado,
            procedimentos_com_oncologico: set[str]) -> list[PropostaRegra]:
    corte = _utc(referencia) - timedelta(days=params.janela_dias)
    grupos: dict[tuple[str, MotivoCodificado, Classe], list[CasoAprendizado]] = {}
    for c in casos:
        if _utc(c.data) >= corte:
            grupos.setdefault((c.procedimento_id, c.motivo, c.classe_de), []).append(c)

    propostas: list[PropostaRegra] = []
    for (proc, motivo, de), grupo in grupos.items():
        total = len(grupo)
        por_para: dict[Classe, list[CasoAprendizado]] = {}
        for c in grupo:
            if c.classe_para != de:
                por_para.setdefault(c.classe_para, []).append(c)
        for para, cs in por_para.items():
            n_reg = len({c.regulador_id for c in cs})
            consistencia = len(cs) / total
            if (len(cs) < params.min_casos or n_reg < params.min_reguladores
                    or consistencia < params.min_consistencia):
                continue
            dirc = direcao(de, para)
            status, descarte = "pendente", None
            if dirc == "rebaixar" and proc in procedimentos_com_oncologico:
                status = "descartada"
                descarte = ("I-01: o procedimento tem paciente oncológico ativo; "
                            "rebaixar classe não pode ser proposto")
            propostas.append(PropostaRegra(
                proposta_id=proposta_id(proc, motivo, de, para), procedimento_id=proc,
                motivo=motivo, classe_de=de, classe_para=para, direcao=dirc,
                n_casos=len(cs), n_reguladores=n_reg, consistencia=round(consistencia, 2),
                casos=sorted(c.decisao_id for c in cs), status=status, motivo_descarte=descarte))
    propostas.sort(key=lambda p: (p.status != "pendente", -p.n_casos, p.proposta_id))
    return propostas
