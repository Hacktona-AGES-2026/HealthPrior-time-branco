"""Tabelas da carga inicial (US-01).

As colunas dos CSVs entram com o nome original e sem alteração de valor (vazio vira NULL).
Colunas normalizadas (cid_norm etc.) entram na US-02, como colunas novas.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Marca colunas que não vêm do CSV: a carga não as escreve nem as sobrescreve.
SISTEMA = {"sistema": True}


class Procedimento(Base):
    __tablename__ = "procedimentos"

    procedimento_id: Mapped[str] = mapped_column(String, primary_key=True)
    procedimento: Mapped[Optional[str]] = mapped_column(String)
    especialidade: Mapped[Optional[str]] = mapped_column(String)
    porte: Mapped[Optional[str]] = mapped_column(String)
    risco_cirurgico: Mapped[Optional[int]] = mapped_column(Integer)
    duracao_media_min: Mapped[Optional[int]] = mapped_column(Integer)
    necessita_uti: Mapped[Optional[str]] = mapped_column(String)


class Solicitacao(Base):
    __tablename__ = "solicitacoes"

    # --- colunas de data/fila_cirurgica.csv, na ordem do arquivo ---
    solicitacao_id: Mapped[str] = mapped_column(String, primary_key=True)
    paciente_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    nome_paciente: Mapped[Optional[str]] = mapped_column(String)
    sexo: Mapped[Optional[str]] = mapped_column(String)
    idade: Mapped[Optional[int]] = mapped_column(Integer)
    municipio: Mapped[Optional[str]] = mapped_column(String)
    uf: Mapped[Optional[str]] = mapped_column(String)
    distancia_hospital_km: Mapped[Optional[int]] = mapped_column(Integer)
    procedimento_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("procedimentos.procedimento_id")
    )
    procedimento: Mapped[Optional[str]] = mapped_column(String)
    especialidade: Mapped[Optional[str]] = mapped_column(String)
    cid_principal: Mapped[Optional[str]] = mapped_column(String)
    cid_descricao: Mapped[Optional[str]] = mapped_column(String)
    cid_secundario: Mapped[Optional[str]] = mapped_column(String)
    asa: Mapped[Optional[int]] = mapped_column(Integer)
    comorbidades: Mapped[Optional[str]] = mapped_column(String)
    intensidade_dor_eva: Mapped[Optional[int]] = mapped_column(Integer)
    limitacao_funcional: Mapped[Optional[str]] = mapped_column(String)
    justificativa_clinica: Mapped[Optional[str]] = mapped_column(Text)
    observacoes: Mapped[Optional[str]] = mapped_column(Text)
    data_entrada_fila: Mapped[Optional[date]] = mapped_column(Date)
    dias_em_fila: Mapped[Optional[int]] = mapped_column(Integer)
    prioridade_regulacao: Mapped[Optional[str]] = mapped_column(String)
    data_ultima_revisao_prioridade: Mapped[Optional[date]] = mapped_column(Date)
    flag_oncologico: Mapped[Optional[str]] = mapped_column(String)
    flag_diabetico: Mapped[Optional[str]] = mapped_column(String)
    flag_piora_clinica: Mapped[Optional[str]] = mapped_column(String)
    hba1c_ultima: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1))
    data_hba1c_ultima: Mapped[Optional[date]] = mapped_column(Date)
    avaliacao_pre_anestesica: Mapped[Optional[str]] = mapped_column(String)
    exames_pre_op_validos: Mapped[Optional[str]] = mapped_column(String)

    # --- estado do sistema (não vêm do CSV; a recarga não os sobrescreve) ---
    # D-01: a carga inicial não passa pelo regulador.
    classe_status: Mapped[str] = mapped_column(
        String, nullable=False, default="sugerida_nao_confirmada",
        server_default="sugerida_nao_confirmada", info=SISTEMA,
    )
    status_fila: Mapped[str] = mapped_column(
        String, nullable=False, default="ativa", server_default="ativa", info=SISTEMA
    )

    # --- colunas normalizadas (US-02); recalculadas a cada normalização ---
    cid_norm: Mapped[Optional[str]] = mapped_column(String, info=SISTEMA)  # PRE-01
    nome_norm: Mapped[Optional[str]] = mapped_column(String, info=SISTEMA)  # PRE-02
    municipio_norm: Mapped[Optional[str]] = mapped_column(String, info=SISTEMA)  # PRE-03
    prioridade_norm: Mapped[Optional[str]] = mapped_column(String, info=SISTEMA)  # PRE-04


class CorrecaoLog(Base):
    """Toda correção automática do pré-processamento: campo, original, novo e regra."""

    __tablename__ = "correcoes_log"
    __table_args__ = (Index("ix_correcoes_log_solicitacao_id", "solicitacao_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id: Mapped[str] = mapped_column(ForeignKey("solicitacoes.solicitacao_id"))
    campo: Mapped[str] = mapped_column(String, nullable=False)
    original: Mapped[Optional[str]] = mapped_column(Text)
    novo: Mapped[Optional[str]] = mapped_column(Text)
    regra: Mapped[str] = mapped_column(String, nullable=False)


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (Index("ix_eventos_solicitacao_id", "solicitacao_id"),)

    # Sem FK em solicitacao_id: há eventos órfãos no dataset e nada é apagado (I-03);
    # a US-04 os sinaliza como pendência.
    evento_id: Mapped[str] = mapped_column(String, primary_key=True)
    solicitacao_id: Mapped[Optional[str]] = mapped_column(String)
    paciente_id: Mapped[Optional[str]] = mapped_column(String)
    data_evento: Mapped[Optional[date]] = mapped_column(Date)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String)
    resultado: Mapped[Optional[str]] = mapped_column(String)
    valor_numerico: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 1))
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    origem: Mapped[Optional[str]] = mapped_column(String)
