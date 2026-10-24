"""Entidades do domínio. Python puro: sem pandas, sem FastAPI, sem banco.

Nomes de campos seguem o dataset e docs/fluxo-sistema.md §8.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.enums import (
    AcaoDecisao,
    Camada,
    Classe,
    ClasseStatus,
    MotivoCodificado,
    StatusFila,
    StatusPendencia,
)


@dataclass
class Solicitacao:
    """Uma linha da fila. Campos originais + normalizados + estado do sistema."""

    solicitacao_id: str
    paciente_id: str
    procedimento_id: str
    cid_principal: str
    data_entrada_fila: date
    # originais relevantes (os demais ficam no banco)
    nome_paciente: str = ""
    idade: int | None = None
    sexo: str | None = None
    municipio: str | None = None
    procedimento: str | None = None
    especialidade: str | None = None
    cid_descricao: str | None = None
    intensidade_dor_eva: int | None = None
    limitacao_funcional: str | None = None
    justificativa_clinica: str = ""
    observacoes: str = ""
    prioridade_regulacao: str | None = None
    flag_oncologico: str | None = None
    flag_piora_clinica: str | None = None
    # normalizados (PRE-01..PRE-06)
    cid_norm: str = ""
    nome_norm: str = ""
    oncologico: bool = False
    municipio_norm: str | None = None
    prioridade_norm: str | None = None
    piora_recalculada: bool | None = None
    # estado
    status_fila: StatusFila = StatusFila.ATIVA
    motivo_status: str | None = None
    classe_status: ClasseStatus = ClasseStatus.SUGERIDA_NAO_CONFIRMADA
    alertas: list[str] = field(default_factory=list)
    # override do regulador (C-10)
    classe_medico: Classe | None = None
    score_medico: float | None = None
    editado_manualmente: bool = False
    editado_por: str | None = None
    editado_em: datetime | None = None


@dataclass
class Evento:
    evento_id: str
    solicitacao_id: str
    paciente_id: str
    data_evento: date
    tipo_evento: str
    resultado: str | None = None
    valor_numerico: float | None = None
    descricao: str = ""
    origem: str | None = None
    # PRE-07, PRE-08, PRE-24
    duplicado_de: str | None = None
    historico: bool = False
    orfao: bool = False


@dataclass
class Motivo:
    """Sinal que levou a uma classe, com evidência citável (explicabilidade)."""

    sinal: str
    evidencia: str
    fonte: str  # "evento" | "justificativa_clinica" | "observacoes" | "cid"
    ref: str | None = None
    data: date | None = None


@dataclass
class ResultadoScore:
    """Contrato de saída do SWALIS (docs/fluxo-sistema.md C-07)."""

    classe_sistema: Classe
    prazo_dias: int
    pct_prazo_consumido: float
    score_sistema: float
    motivos: list[Motivo]
    versao_regras: str


@dataclass
class Achado:
    """Resultado de uma regra de pré-processamento (PRE-xx)."""

    regra: str
    bloqueante: bool
    titulo: str
    evidencias: list[Motivo] = field(default_factory=list)
    acao_sugerida: str = ""


@dataclass
class Correcao:
    """Correção automática registrada (I-10)."""

    solicitacao_id: str
    campo: str
    original: str | None
    novo: str | None
    regra: str


@dataclass
class Pendencia:
    pendencia_id: str
    solicitacao_id: str
    regra: str
    titulo: str
    bloqueante: bool
    evidencias: list[Motivo]
    acao_sugerida: str
    status: StatusPendencia = StatusPendencia.ABERTA
    aberta_em: date | None = None
    resolvido_por: str | None = None
    resolvido_em: datetime | None = None
    resolucao: str | None = None


@dataclass
class Decisao:
    decisao_id: str
    solicitacao_id: str
    regulador_id: str
    acao: AcaoDecisao
    data: datetime
    classe_sugerida: Classe | None
    classe_decidida: Classe | None
    score_decidido: float | None = None
    motivo_codificado: MotivoCodificado | None = None
    justificativa: str | None = None
    versao_regras: str | None = None


@dataclass
class ItemRanking:
    """Entrada da trava (C-11): só o que a ordenação precisa saber."""

    solicitacao_id: str
    oncologico: bool
    urgente: bool
    score_efetivo: float
    data_entrada_fila: date


@dataclass
class ItemFila:
    """Saída da trava: posição final."""

    posicao: int
    solicitacao_id: str
    camada: Camada
    score_efetivo: float


@dataclass
class ResultadoTabela:
    """Contagem da carga de uma tabela (US-01)."""

    lido: int = 0
    inseridos: int = 0
    atualizados: int = 0


@dataclass
class LinhaFila:
    """Uma linha da fila priorizada já calculada (saída de montar_fila, US-08/09)."""

    solicitacao_id: str
    posicao: int
    justificativa: str
    camada: int
    classe: str
    pct_prazo_consumido: float
    dias_em_fila: int
    score_efetivo: float
    editado_manualmente: bool
    versao_regras: str
