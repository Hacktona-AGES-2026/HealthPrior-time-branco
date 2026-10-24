"""Contrato da API (docs/user-stories.md §5). Fonte dos tipos do front (OpenAPI).

Mudou aqui? Atualize docs/user-stories.md §5 no mesmo PR.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.domain.enums import (
    AcaoDecisao,
    Classe,
    ClasseStatus,
    DesfechoEvento,
    MotivoCodificado,
    ResolucaoPendencia,
    StatusFila,
    StatusPendencia,
)

CamadaInt = Literal[1, 2, 3]


class Erro(BaseModel):
    erro: str
    mensagem: str


# ---------- admin ----------
class ResultadoTabelaOut(BaseModel):
    lido: int
    inseridos: int
    atualizados: int


class NormalizacaoOut(BaseModel):
    solicitacoes: int
    correcoes: int
    por_regra: dict[str, int]


class FlagsOut(BaseModel):
    solicitacoes: int
    eventos_duplicados: int
    eventos_historicos: int
    correcoes: dict[str, int]  # por regra (PRE-xx)


class PendenciasSincronizadasOut(BaseModel):
    abertas: int
    atualizadas: int
    encerradas: int


class InconsistenciasOut(BaseModel):
    solicitacoes: int
    alertas: dict[str, int]  # por regra (PRE-xx)
    pendencias: PendenciasSincronizadasOut


class BloqueantesOut(BaseModel):
    solicitacoes: int
    achados: dict[str, int]  # por regra (PRE-xx)
    suspensas: int
    reativadas: int
    oncologicas_a_confirmar: int
    eventos_orfaos: int
    pendencias: PendenciasSincronizadasOut


class CargaOut(BaseModel):
    procedimentos: ResultadoTabelaOut
    solicitacoes: ResultadoTabelaOut
    eventos: ResultadoTabelaOut
    normalizacao: NormalizacaoOut
    flags: Optional[FlagsOut] = None
    inconsistencias: Optional[InconsistenciasOut] = None
    bloqueantes: Optional[BloqueantesOut] = None


# ---------- fila ----------
class ItemFilaOut(BaseModel):
    posicao: int
    solicitacao_id: str
    camada: CamadaInt
    classe: Optional[Classe]
    classe_status: ClasseStatus
    pct_prazo_consumido: Optional[float]
    dias_em_fila: int
    procedimento: str
    especialidade: str
    cid: str
    oncologico: bool
    editado_manualmente: bool
    alertas: list[str] = []
    resumo_justificativa: str


class FilaOut(BaseModel):
    versao_regras: str
    gerada_em: datetime
    publicada: bool
    total: int
    itens: list[ItemFilaOut]


# ---------- detalhe ----------
class MotivoOut(BaseModel):
    sinal: str
    evidencia: str
    fonte: str
    ref: Optional[str] = None
    data: Optional[date] = None


class ScoreOut(BaseModel):
    classe_sistema: Optional[Classe]
    score_sistema: Optional[float]
    classe_medico: Optional[Classe] = None
    score_medico: Optional[float] = None
    score_efetivo: Optional[float]
    prazo_dias: Optional[int]
    pct_prazo_consumido: Optional[float]
    classe_status: ClasseStatus
    versao_regras: Optional[str]
    motivos: list[MotivoOut] = []


class EventoOut(BaseModel):
    evento_id: str
    data_evento: date
    tipo_evento: str
    resultado: Optional[str] = None
    descricao: Optional[str] = None
    historico: bool = False
    duplicado: bool = False


class DecisaoOut(BaseModel):
    decisao_id: str
    data: datetime
    regulador_id: str
    acao: AcaoDecisao
    classe_decidida: Optional[Classe] = None
    motivo_codificado: Optional[MotivoCodificado] = None
    justificativa: Optional[str] = None


class PendenciaResumoOut(BaseModel):
    pendencia_id: str
    regra: str
    bloqueante: bool
    status: StatusPendencia


class CorrecaoOut(BaseModel):
    campo: str
    original: Optional[str]
    novo: Optional[str]
    regra: str


class SolicitacaoDetalheOut(BaseModel):
    solicitacao_id: str
    paciente_id: str
    nome_paciente: str
    idade: Optional[int]
    sexo: Optional[str]
    municipio: Optional[str]
    procedimento: str
    cid: str
    cid_descricao: Optional[str]
    status_fila: StatusFila
    posicao: Optional[int]
    camada: Optional[CamadaInt]
    camada_motivo: Optional[str]
    score: ScoreOut
    explicacao: str
    eventos: list[EventoOut] = []
    decisoes: list[DecisaoOut] = []
    pendencias: list[PendenciaResumoOut] = []
    alertas: list[str] = []
    correcoes: list[CorrecaoOut] = []


# ---------- inbox ----------
class EditadoAnteriormente(BaseModel):
    por: str
    em: date


class ItemInboxOut(BaseModel):
    solicitacao_id: str
    procedimento: str
    camada: CamadaInt
    dias_em_fila: int
    classe_atual: Optional[Classe]
    classe_sugerida: Classe
    motivos: list[MotivoOut]
    evento_gatilho: Optional[str] = None
    editado_anteriormente: Optional[EditadoAnteriormente] = None
    criado_em: datetime


class InboxOut(BaseModel):
    total: int
    itens: list[ItemInboxOut]


# ---------- decisões ----------
class DecisaoIn(BaseModel):
    solicitacao_id: str
    regulador_id: str
    acao: AcaoDecisao
    classe: Optional[Classe] = None
    score: Optional[float] = None
    motivo_codificado: Optional[MotivoCodificado] = None
    justificativa: Optional[str] = None


class DecisaoResultadoOut(BaseModel):
    decisao_id: str
    posicao_anterior: Optional[int]
    posicao_nova: Optional[int]
    fila_publicada: bool


# ---------- eventos ----------
class EventoIn(BaseModel):
    solicitacao_id: str
    data_evento: date
    tipo_evento: str
    resultado: Optional[str] = None
    valor_numerico: Optional[float] = None
    descricao: str = ""
    origem: Optional[str] = None


class EventoResultadoOut(BaseModel):
    evento_id: str
    desfecho: DesfechoEvento
    classe_antes: Optional[Classe]
    classe_depois: Optional[Classe]
    pendencia_id: Optional[str] = None


# ---------- pendências ----------
class EvidenciaOut(BaseModel):
    fonte: str
    ref: Optional[str] = None
    texto: str


class PendenciaOut(BaseModel):
    pendencia_id: str
    solicitacao_id: str
    regra: str
    titulo: str
    bloqueante: bool
    evidencias: list[EvidenciaOut]
    acao_sugerida: str
    status: StatusPendencia
    aberta_em: date


class PendenciasOut(BaseModel):
    total: int
    itens: list[PendenciaOut]


class ResolverPendenciaIn(BaseModel):
    resolucao: ResolucaoPendencia
    usuario_id: str
    observacao: Optional[str] = None
    fundir_com: Optional[str] = Field(default=None, description="solicitacao_id que permanece")


class ResolverPendenciaOut(BaseModel):
    status_fila: StatusFila
    fila_publicada: bool
