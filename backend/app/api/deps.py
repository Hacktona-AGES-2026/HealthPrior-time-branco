"""Composição (injeção de dependências manual). Único lugar que conhece implementações concretas.

Rotas recebem casos de uso prontos via Depends; trocar SwalisStub pelo SWALIS real é só aqui.
"""
from fastapi import Depends
from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.decidir import DecidirClasse
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.application.gerar_fila import GerarFila
from app.application.registrar_evento import RegistrarEvento
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlEventoRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_stub import SwalisStub


def get_scorer():
    return SwalisStub()  # TODO(SWALIS): trocar pela implementação real


def get_carga_inicial(session: Session = Depends(get_session)) -> CargaInicial:
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    flags = RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                            SqlCorrecaoRepository(session))
    return CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session), flags)


def get_gerar_fila(session: Session = Depends(get_session)) -> GerarFila:
    return GerarFila(
        solicitacoes=SqlSolicitacaoRepository(session),
        eventos=SqlEventoRepository(session),
        scorer=get_scorer(),
        exportador=ExportadorCsv(),
        ref_date=settings.ref_date,
    )


def get_registrar_evento(session: Session = Depends(get_session)) -> RegistrarEvento:
    return RegistrarEvento(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           get_scorer(), pendencias=None)


def get_decidir(session: Session = Depends(get_session),
                gerar_fila: GerarFila = Depends(get_gerar_fila)) -> DecidirClasse:
    return DecidirClasse(SqlSolicitacaoRepository(session), decisoes=None, gerar_fila=gerar_fila)
