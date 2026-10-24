"""Composição (injeção de dependências manual). Único lugar que conhece implementações concretas.

Rotas recebem casos de uso prontos via Depends; trocar a implementação do SWALIS é só aqui.
"""
from datetime import datetime, timezone

from fastapi import Depends
from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.decidir import DecidirClasse
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.application.gerar_fila import GerarFila
from app.application.publicar_fila import ExportarFilaPublicada, PublicarFila
from app.application.registrar_evento import RegistrarEvento
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlPendenciaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.verificador import VerificadorOficial


def get_scorer():
    return criar_swalis()


def get_carga_inicial(session: Session = Depends(get_session)) -> CargaInicial:
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    flags = RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                            SqlCorrecaoRepository(session))
    inconsistencias = DetectarInconsistencias(
        SqlSolicitacaoRepository(session), SqlEventoRepository(session),
        SqlPendenciaRepository(session), settings.ref_date)
    return CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session), flags, inconsistencias)


def get_gerar_fila(session: Session = Depends(get_session)) -> GerarFila:
    return GerarFila(
        solicitacoes=SqlSolicitacaoRepository(session),
        eventos=SqlEventoRepository(session),
        scorer=get_scorer(),
        exportador=ExportadorCsv(),
        ref_date=settings.ref_date,
    )


def get_publicar_fila(session: Session = Depends(get_session),
                      gerar: GerarFila = Depends(get_gerar_fila)) -> PublicarFila:
    return PublicarFila(
        gerar=gerar,
        verificador=VerificadorOficial(),
        fila=SqlFilaRepository(session),
        uow=SqlUnidadeDeTrabalho(session),
        relogio=lambda: datetime.now(timezone.utc),
        output_dir=settings.output_dir,
    )


def get_exportar_fila_publicada(session: Session = Depends(get_session)) -> ExportarFilaPublicada:
    return ExportarFilaPublicada(SqlFilaRepository(session), ExportadorCsv(), settings.output_dir)


def get_registrar_evento(session: Session = Depends(get_session)) -> RegistrarEvento:
    return RegistrarEvento(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           get_scorer(), pendencias=None)


def get_decidir(session: Session = Depends(get_session),
                gerar_fila: GerarFila = Depends(get_gerar_fila)) -> DecidirClasse:
    return DecidirClasse(SqlSolicitacaoRepository(session), decisoes=None, gerar_fila=gerar_fila)
