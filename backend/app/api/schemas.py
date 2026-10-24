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


class RecontatoOut(BaseModel):
    """US-17: quem passou de N dias sem evento e o que mudou nas pendências de recontato."""

    n_dias: int
    sem_evento: int
    abertas: int
    atualizadas: int
    encerradas: int


class PublicacaoOut(BaseModel):
    publicada: bool
    total: int
    por_camada: dict[int, int]
    versao_regras: str
    saida_verificador: str
    data_referencia: date  # US-16: data usada no cálculo (avança na atualização diária)
    recontato: Optional["RecontatoOut"] = None  # US-17: só na atualização diária


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
    iniciais: str = ""
    idade: Optional[int] = None
    sexo: Optional[str] = None
    municipio: Optional[str] = None
    cid_descricao: Optional[str] = None
    intensidade_dor_eva: Optional[int] = None
    limitacao_funcional: Optional[str] = None
    posicao_antes: Optional[int] = None


class FilaOut(BaseModel):
    versao_regras: Optional[str] = None
    gerada_em: Optional[datetime] = None
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


class EvidenciaOut(BaseModel):
    fonte: str
    ref: Optional[str] = None
    texto: str


class SugestaoCidOut(BaseModel):
    """PRE-12 (D-117): CID sugerido pelo LLM a partir do laudo. Só sugestão; o regulador decide (I-05)."""
    cid: str
    descricao: str = Field(description="descrição oficial da tabela CID-10")
    citacao: str = Field(description="trecho literal do laudo que justifica o CID")
    confianca: float
    modelo: str
    evento_id: Optional[str] = None


class PendenciaResumoOut(BaseModel):
    pendencia_id: str
    regra: str
    bloqueante: bool
    status: StatusPendencia
    titulo: Optional[str] = None
    evidencias: list[EvidenciaOut] = []
    sugestao_cid: Optional[SugestaoCidOut] = None


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
    cid_original: Optional[str] = Field(
        default=None, description="CID do cadastro quando o regulador corrigiu o CID (PRE-12, D-117)")
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
    criado_em: Optional[datetime] = None


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
class PendenciaOut(BaseModel):
    pendencia_id: str
    solicitacao_id: str
    regra: str
    titulo: str
    bloqueante: bool
    evidencias: list[EvidenciaOut]
    acao_sugerida: str
    sugestao_cid: Optional[SugestaoCidOut] = None
    status: StatusPendencia
    aberta_em: date
    # preenchidos depois de resolvida (US-07); ficam null enquanto a pendência está aberta
    resolvido_por: Optional[str] = None
    resolvido_em: Optional[datetime] = None
    resolucao: Optional[str] = None
    observacao: Optional[str] = None


class PendenciasOut(BaseModel):
    total: int
    itens: list[PendenciaOut]


class ResolverPendenciaIn(BaseModel):
    resolucao: ResolucaoPendencia
    usuario_id: str
    observacao: Optional[str] = None
    fundir_com: Optional[str] = Field(default=None, description="solicitacao_id que permanece")
    cid: Optional[str] = Field(default=None, description="corrigir_cid (PRE-12): o CID novo, ex. C50.9")


class ResolverPendenciaOut(BaseModel):
    status_fila: Optional[StatusFila] = Field(
        default=None, description="da solicitação da pendência; null quando não há (PRE-24, evento órfão)")
    fila_publicada: bool = Field(description="false: o verificador reprovou e a fila anterior segue publicada (I-07)")


# US-22
class IndicadoresOut(BaseModel):
    total: int
    violacoes_regra_ouro: int
    posicao_mediana_oncologicos: Optional[float] = None
    pct_oncologicos_primeiro_terco: float
    pct_ps_recente_primeira_metade: float
    pct_sem_urgencia_ultimo_terco: float


class DestaqueOut(BaseModel):
    solicitacao_id: str
    posicao_antes: Optional[int] = None
    posicao_depois: Optional[int] = None
    camada_depois: Optional[int] = None


class ComparacaoOut(BaseModel):
    antes: IndicadoresOut
    depois: Optional[IndicadoresOut] = None
    publicada: bool
    destaques: list[DestaqueOut]


# ---------- US-18 · aprendizado ----------
class ParametrosAprendizadoIn(BaseModel):
    """Parâmetros do agrupamento (Q-05, provisórios). Omitidos ficam no padrão."""

    min_casos: Optional[int] = Field(default=None, gt=0)
    min_reguladores: Optional[int] = Field(default=None, gt=0)
    janela_dias: Optional[int] = Field(default=None, gt=0)
    min_consistencia: Optional[float] = Field(default=None, gt=0, le=1)


class PropostaRegraOut(BaseModel):
    proposta_id: str
    procedimento_id: str
    procedimento: Optional[str] = None
    motivo: MotivoCodificado
    classe_de: Classe
    classe_para: Classe
    direcao: Literal["subir", "rebaixar"]
    n_casos: int
    n_reguladores: int
    consistencia: float
    casos: list[str]
    status: Literal["pendente", "descartada", "aprovada", "rejeitada", "revertida"]
    motivo_descarte: Optional[str] = None


class GerarPropostasOut(BaseModel):
    analisadas: int
    consideradas: int
    outros_reclassificados: int
    outros_sem_grupo: int
    propostas: list[PropostaRegraOut]
    descartadas: list[PropostaRegraOut]


class CasoOrigemOut(BaseModel):
    decisao_id: str
    solicitacao_id: str
    regulador_id: str
    data: datetime
    acao: str
    classe_de: Optional[Classe] = None
    classe_para: Optional[Classe] = None
    motivo: Optional[MotivoCodificado] = None
    justificativa: Optional[str] = None


class ImpactoOut(BaseModel):
    """Shadow run: o que a regra mudaria na fila de hoje, sem aplicar."""

    afetados: int
    oncologicos_afetados: int
    oncologicos_rebaixados: int  # tem de ser 0 (I-01)
    exemplos: list[str]


class PropostaDetalheOut(PropostaRegraOut):
    casos_origem: list[CasoOrigemOut]
    impacto: Optional[ImpactoOut] = None  # só nas pendentes
    decidida_por: Optional[str] = None
    decidida_em: Optional[datetime] = None
    observacao: Optional[str] = None
    versao: Optional[int] = None  # versão de regras criada, nas aprovadas e revertidas
    revertida_por: Optional[str] = None
    revertida_em: Optional[datetime] = None
    motivo_reversao: Optional[str] = None


class PropostasOut(BaseModel):
    total: int
    itens: list[PropostaDetalheOut]


class DecidirPropostaIn(BaseModel):
    decisao: Literal["aprovar", "rejeitar"]
    usuario_id: str
    observacao: Optional[str] = None


class DecidirPropostaOut(BaseModel):
    proposta_id: str
    status: Literal["aprovada", "rejeitada"]
    versao: Optional[int] = None
    versao_regras: Optional[str] = None
    enviados_ao_inbox: int


class ReverterRegraIn(BaseModel):
    usuario_id: str
    motivo: str


class ReverterRegraOut(BaseModel):
    regra_id: str
    status: Literal["revertida"]
    versao_regras: str
    devolvidos_ao_inbox: int


class NotificacaoOut(BaseModel):
    notificacao_id: str
    solicitacao_id: str
    motivo: Literal["posicao", "situacao", "recontato"]
    texto: str
    canal: str
    status: Literal["pendente", "enviada", "falhou"]
    criada_em: Optional[datetime] = None
    enviada_em: Optional[datetime] = None
    tentativas: int
    detalhe: Optional[str] = None


class NotificacoesOut(BaseModel):
    canal: str  # simulado | twilio (o que está configurado agora)
    destino: Optional[str] = None  # número da demo, mascarado
    total: int
    itens: list[NotificacaoOut]


class EnviosOut(BaseModel):
    canal: str
    enviadas: int
    falhas: int
    pendentes: int
