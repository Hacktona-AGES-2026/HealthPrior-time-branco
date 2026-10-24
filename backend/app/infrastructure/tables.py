"""Tabelas do banco. Espelham o dataset (colunas originais) + colunas novas (docs/fluxo-sistema.md §8).

Colunas originais nunca são sobrescritas; normalizações vão para colunas *_norm (I-10).
Listas/estruturas vão como JSON em texto (simples para hackathon).
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ProcedimentoTable(SQLModel, table=True):
    __tablename__ = "procedimentos"

    procedimento_id: str = Field(primary_key=True)
    procedimento: Optional[str] = None
    especialidade: Optional[str] = None
    porte: Optional[str] = None
    risco_cirurgico: Optional[int] = None
    duracao_media_min: Optional[int] = None
    necessita_uti: Optional[str] = None


class SolicitacaoTable(SQLModel, table=True):
    __tablename__ = "solicitacoes"

    # --- originais (fila_cirurgica.csv) ---
    solicitacao_id: str = Field(primary_key=True)
    paciente_id: str = Field(index=True)
    nome_paciente: str
    sexo: Optional[str] = None
    idade: Optional[int] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    distancia_hospital_km: Optional[int] = None
    procedimento_id: str = Field(index=True)
    procedimento: Optional[str] = None
    especialidade: Optional[str] = None
    cid_principal: str
    cid_descricao: Optional[str] = None
    cid_secundario: Optional[str] = None
    asa: Optional[int] = None
    comorbidades: Optional[str] = None
    intensidade_dor_eva: Optional[int] = None
    limitacao_funcional: Optional[str] = None
    justificativa_clinica: Optional[str] = None
    observacoes: Optional[str] = None
    data_entrada_fila: date
    dias_em_fila: Optional[int] = None
    prioridade_regulacao: Optional[str] = None
    data_ultima_revisao_prioridade: Optional[date] = None
    flag_oncologico: Optional[str] = None
    flag_diabetico: Optional[str] = None
    flag_piora_clinica: Optional[str] = None
    hba1c_ultima: Optional[float] = None
    data_hba1c_ultima: Optional[date] = None
    avaliacao_pre_anestesica: Optional[str] = None
    exames_pre_op_validos: Optional[str] = None

    # --- normalizados (PRE-01..PRE-06) ---
    cid_norm: str = Field(default="", index=True)
    oncologico: bool = Field(default=False, index=True)
    nome_norm: Optional[str] = None
    municipio_norm: Optional[str] = None
    prioridade_norm: Optional[str] = None
    piora_recalculada: Optional[bool] = None

    # --- estado ---
    status_fila: str = Field(default="ativa", index=True)
    motivo_status: Optional[str] = None
    alertas_json: str = "[]"
    ultimo_evento_em: Optional[date] = None

    # --- score (saída do SWALIS) ---
    classe_sistema: Optional[str] = None
    score_sistema: Optional[float] = None
    prazo_dias: Optional[int] = None
    pct_prazo_consumido: Optional[float] = None
    motivos_json: str = "[]"
    versao_regras: Optional[str] = None
    classe_status: str = "sugerida_nao_confirmada"

    # --- override do regulador (C-10) ---
    classe_medico: Optional[str] = None
    classe_confirmada: Optional[str] = None  # US-13 preenche; US-12 só lê
    score_medico: Optional[float] = None
    editado_manualmente: bool = False
    editado_por: Optional[str] = None
    editado_em: Optional[datetime] = None
    motivo_codificado: Optional[str] = None
    justificativa_medico: Optional[str] = None


class EventoTable(SQLModel, table=True):
    __tablename__ = "eventos"

    evento_id: str = Field(primary_key=True)
    solicitacao_id: str = Field(index=True)
    paciente_id: str = Field(index=True)
    data_evento: date
    tipo_evento: str
    resultado: Optional[str] = None
    valor_numerico: Optional[float] = None
    descricao: Optional[str] = None
    origem: Optional[str] = None
    # PRE-07, PRE-08, PRE-24
    duplicado_de: Optional[str] = None
    historico: bool = False
    orfao: bool = False
    processado_em: Optional[datetime] = None
    mudou_classe: Optional[bool] = None


class CorrecaoTable(SQLModel, table=True):
    __tablename__ = "correcoes_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitacao_id: str = Field(index=True)
    campo: str
    original: Optional[str] = None
    novo: Optional[str] = None
    regra: str
    criado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PendenciaTable(SQLModel, table=True):
    __tablename__ = "pendencias"

    pendencia_id: str = Field(primary_key=True)
    solicitacao_id: str = Field(index=True)
    regra: str = Field(index=True)
    titulo: str
    bloqueante: bool
    evidencias_json: str = "[]"
    acao_sugerida: Optional[str] = None
    status: str = Field(default="aberta", index=True)
    aberta_em: date
    resolvido_por: Optional[str] = None
    resolvido_em: Optional[datetime] = None
    resolucao: Optional[str] = None
    observacao: Optional[str] = None


class DecisaoTable(SQLModel, table=True):
    __tablename__ = "decisoes"

    decisao_id: str = Field(primary_key=True)
    solicitacao_id: str = Field(index=True)
    procedimento_id: Optional[str] = None
    regulador_id: str = Field(index=True)
    acao: str
    data: datetime
    classe_sugerida: Optional[str] = None
    classe_decidida: Optional[str] = None
    score_decidido: Optional[float] = None
    motivo_codificado: Optional[str] = None
    justificativa: Optional[str] = None
    versao_regras: Optional[str] = None


class PropostaRegraTable(SQLModel, table=True):
    """US-18: proposta de regra agrupada das decisões. A US-19 aprova/rejeita (campos decidida_*)."""

    __tablename__ = "propostas_regra"

    proposta_id: str = Field(primary_key=True)
    procedimento_id: str = Field(index=True)
    motivo: str
    classe_de: str
    classe_para: str
    direcao: str
    n_casos: int
    n_reguladores: int
    consistencia: float
    casos: str = ""  # decisao_ids separados por vírgula
    status: str = Field(index=True)  # pendente | descartada | aprovada | rejeitada
    motivo_descarte: Optional[str] = None
    gerada_em: datetime
    decidida_por: Optional[str] = None
    decidida_em: Optional[datetime] = None
    observacao: Optional[str] = None


class RegraAprendidaTable(SQLModel, table=True):
    """US-19: regra aprovada pelo comitê. Cada aprovação abre a versão N+1; `ativa=False` reverte."""

    __tablename__ = "regras_aprendidas"

    regra_id: str = Field(primary_key=True)  # o proposta_id que a originou
    procedimento_id: str = Field(index=True)
    classe_de: str
    classe_para: str
    versao: int = Field(index=True)
    aprovada_por: str
    aprovada_em: datetime
    ativa: bool = True


class FilaPublicadaTable(SQLModel, table=True):
    __tablename__ = "fila_publicada"

    solicitacao_id: str = Field(primary_key=True)
    posicao: int = Field(index=True)
    camada: int
    classe: str
    pct_prazo_consumido: float
    dias_em_fila: int
    score_efetivo: float
    justificativa: str
    editado_manualmente: bool = False
    versao_regras: str
    publicada_em: datetime  # relógio real (quando foi publicada)
    # US-16: data de referência usada no cálculo (dias em fila, % do prazo). Nasce em HP_REF_DATE e
    # só avança pela atualização diária (relógio simulado da demo). Coluna nova: recriar o banco.
    data_referencia: date
