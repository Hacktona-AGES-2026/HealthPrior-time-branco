"""Composição (injeção de dependências manual). Único lugar que conhece implementações concretas.

Rotas recebem casos de uso prontos via Depends; trocar a implementação do SWALIS é só aqui.
"""
from datetime import datetime, timezone

from fastapi import Depends
from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.comparar_filas import CompararFilas
from app.application.decidir import DecidirClasse
from app.application.detalhar_solicitacao import DetalharSolicitacao
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.application.gerar_fila import GerarFila
from app.application.listar_fila import ListarFila
from app.application.listar_inbox import ListarInbox
from app.application.publicar_fila import ExportarFilaPublicada, PublicarFila
from app.application.registrar_evento import RegistrarEvento
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlDecisaoRepository,
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


# US-15
def get_registrar_evento(session: Session = Depends(get_session)) -> RegistrarEvento:
    return RegistrarEvento(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           get_scorer(), SqlPendenciaRepository(session),
                           SqlUnidadeDeTrabalho(session))


# US-13/14
def get_decidir(session: Session = Depends(get_session),
                publicar: PublicarFila = Depends(get_publicar_fila)) -> DecidirClasse:
    return DecidirClasse(
        solicitacoes=SqlSolicitacaoRepository(session), eventos=SqlEventoRepository(session),
        decisoes=SqlDecisaoRepository(session), scorer=get_scorer(),
        uow=SqlUnidadeDeTrabalho(session), publicar=publicar, fila=SqlFilaRepository(session),
        relogio=lambda: datetime.now(timezone.utc), ref_date=settings.ref_date)


# US-20
def get_listar_fila(session: Session = Depends(get_session)) -> ListarFila:
    return ListarFila(SqlFilaRepository(session), SqlSolicitacaoRepository(session))


# US-22
DESTAQUES_PADRAO = ["SOL-2023-00010", "SOL-2025-00048", "SOL-2026-00637", "SOL-2026-00757",
                    "SOL-2023-00060"]


def get_comparar_filas(session: Session = Depends(get_session)) -> CompararFilas:
    return CompararFilas(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                         SqlFilaRepository(session), settings.ref_date, DESTAQUES_PADRAO)


# US-12
def get_listar_inbox(session: Session = Depends(get_session)) -> ListarInbox:
    return ListarInbox(SqlFilaRepository(session), SqlSolicitacaoRepository(session),
                       SqlEventoRepository(session), get_scorer(), SqlDecisaoRepository(session))


# US-21
def get_detalhar_solicitacao(session: Session = Depends(get_session)) -> DetalharSolicitacao:
    return DetalharSolicitacao(
        solicitacoes=SqlSolicitacaoRepository(session),
        eventos=SqlEventoRepository(session),
        correcoes=SqlCorrecaoRepository(session),
        pendencias=SqlPendenciaRepository(session),
        fila=SqlFilaRepository(session),
        scorer=get_scorer(),
        ref_date=settings.ref_date,
        decisoes=SqlDecisaoRepository(session),
    )
