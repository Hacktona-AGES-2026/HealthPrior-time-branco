"""Composição (injeção de dependências manual). Único lugar que conhece implementações concretas.

Rotas recebem casos de uso prontos via Depends; trocar a implementação do SWALIS é só aqui.
"""
import logging
from datetime import date, datetime, timezone
from typing import Callable

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.application.atualizacao_diaria import AtualizacaoDiaria
from app.application.carga_inicial import CargaInicial
from app.application.comparar_filas import CompararFilas
from app.application.decidir import DecidirClasse
from app.application.detectar_bloqueantes import DetectarBloqueantes
from app.application.detalhar_solicitacao import DetalharSolicitacao
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.detectar_recontato import DetectarRecontato
from app.application.gerar_propostas import GerarPropostas
from app.application.notificacoes import EnviarNotificacoes, NotificarMudancas
from app.application.propostas import DecidirProposta, ListarPropostas, ReverterRegra
from app.application.listar_pendencias import ListarPendencias
from app.application.normalizar import Normalizar
from app.application.recalcular_flags import RecalcularFlags
from app.application.gerar_fila import GerarFila
from app.application.listar_fila import ListarFila
from app.application.listar_inbox import ListarInbox
from app.application.publicar_fila import ExportarFilaPublicada, PublicarFila
from app.application.registrar_evento import RegistrarEvento
from app.application.resolver_pendencia import ResolverPendencia
from app.application.sugerir_cid import SugerirCid
from app.config import settings
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.db import engine, get_session
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlDecisaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlNotificacaoRepository,
    SqlPendenciaRepository,
    SqlPropostaRepository,
    SqlRegraRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.llm_cid import criar_sugestor_cid
from app.infrastructure.llm_motivos import ClassificadorMotivoLLM
from app.infrastructure.notificador import criar_notificador
from app.infrastructure.swalis_aprendido import com_regras
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.tabela_cid import tabela_cid
from app.infrastructure.verificador import VerificadorOficial


def get_scorer(data: date | None = None):
    return criar_swalis(ref_date=data)


def _scorer(session: Session, data: date | None = None):
    """SWALIS com as regras aprendidas aprovadas pelo comitê (US-19)."""
    return com_regras(get_scorer(data), session, data)


# US-16
def get_data_referencia(session: Session = Depends(get_session)) -> date:
    """Data da última fila publicada (relógio simulado da demo); sem fila, a oficial (HP_REF_DATE).

    Banco fora do ar ou sem a tabela: cai na oficial, para as rotas em mock não dependerem do banco.
    """
    try:
        return SqlFilaRepository(session).data_referencia() or settings.ref_date
    except SQLAlchemyError:
        session.rollback()
        return settings.ref_date


def get_carga_inicial(session: Session = Depends(get_session)) -> CargaInicial:
    normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
    flags = RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                            SqlCorrecaoRepository(session))
    inconsistencias = DetectarInconsistencias(
        SqlSolicitacaoRepository(session), SqlEventoRepository(session),
        SqlPendenciaRepository(session), settings.ref_date)
    bloqueantes = DetectarBloqueantes(
        SqlSolicitacaoRepository(session), SqlEventoRepository(session),
        SqlPendenciaRepository(session), settings.ref_date)
    return CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                        SqlUnidadeDeTrabalho(session), flags, inconsistencias, bloqueantes)


def _gerar_fila_em(session: Session, data: date) -> GerarFila:
    # Uma data só por execução: a mesma vai para o GerarFila e para o SWALIS (% do prazo).
    return GerarFila(
        solicitacoes=SqlSolicitacaoRepository(session),
        eventos=SqlEventoRepository(session),
        scorer=_scorer(session, data),
        exportador=ExportadorCsv(),
        ref_date=data,
    )


def _notificar(session: Session) -> NotificarMudancas:
    """Avisos ao paciente (demo): enfileira nas mudanças e envia pelo canal configurado (simulado por padrão)."""
    repo, uow = SqlNotificacaoRepository(session), SqlUnidadeDeTrabalho(session)
    enviar = EnviarNotificacoes(repo, criar_notificador(), uow, settings.notifica_destino,
                                settings.notifica_limite_envio)
    return NotificarMudancas(repo, uow, criar_notificador().canal, settings.notifica_min_posicoes,
                             settings.notifica_max_por_publicacao, enviar)


def _publicar_fila_em(session: Session, data: date) -> PublicarFila:
    # Com data simulada (US-16) os arquivos vão para output/simulada/: o fila_priorizada.csv
    # oficial (entregável) só é escrito com a data oficial.
    output_dir = settings.output_dir if data == settings.ref_date else settings.output_dir / "simulada"
    return PublicarFila(
        gerar=_gerar_fila_em(session, data),
        verificador=VerificadorOficial(),
        fila=SqlFilaRepository(session),
        uow=SqlUnidadeDeTrabalho(session),
        relogio=lambda: datetime.now(timezone.utc),
        output_dir=output_dir,
        notificar=_notificar(session),
    )


def get_gerar_fila(session: Session = Depends(get_session),
                   data: date = Depends(get_data_referencia)) -> GerarFila:
    return _gerar_fila_em(session, data)


def get_publicar_fila(session: Session = Depends(get_session),
                      data: date = Depends(get_data_referencia)) -> PublicarFila:
    return _publicar_fila_em(session, data)


def _detectar_recontato_em(session: Session, data: date) -> DetectarRecontato:
    return DetectarRecontato(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                             SqlPendenciaRepository(session), data, settings.recontato_dias,
                             notificar=_notificar(session))


def get_atualizacao_diaria(session: Session = Depends(get_session)) -> AtualizacaoDiaria:
    return AtualizacaoDiaria(SqlFilaRepository(session), lambda data: _publicar_fila_em(session, data),
                             settings.ref_date,
                             recontato_em=lambda data: _detectar_recontato_em(session, data),
                             uow=SqlUnidadeDeTrabalho(session))


def get_exportar_fila_publicada(session: Session = Depends(get_session)) -> ExportarFilaPublicada:
    return ExportarFilaPublicada(SqlFilaRepository(session), ExportadorCsv(), settings.output_dir)


def get_listar_pendencias(session: Session = Depends(get_session)) -> ListarPendencias:
    return ListarPendencias(SqlPendenciaRepository(session))


def get_resolver_pendencia(session: Session = Depends(get_session),
                           publicar: PublicarFila = Depends(get_publicar_fila)) -> ResolverPendencia:
    solicitacoes, eventos = SqlSolicitacaoRepository(session), SqlEventoRepository(session)
    correcoes = SqlCorrecaoRepository(session)
    return ResolverPendencia(
        pendencias=SqlPendenciaRepository(session), solicitacoes=solicitacoes, eventos=eventos,
        correcoes=correcoes, uow=SqlUnidadeDeTrabalho(session), publicar=publicar,
        relogio=lambda: datetime.now(timezone.utc),
        recalcular_flags=RecalcularFlags(solicitacoes, eventos, correcoes), notificar=_notificar(session),
        tabela_cid=tabela_cid(settings.data_dir), scorer=_scorer(session))


# PRE-12 · sugestão de CID pelo LLM (D-117)
def montar_sugerir_cid(session: Session) -> SugerirCid:
    return SugerirCid(SqlPendenciaRepository(session), SqlSolicitacaoRepository(session),
                      criar_sugestor_cid(), tabela_cid(settings.data_dir), SqlUnidadeDeTrabalho(session))


def get_sugerir_cid(session: Session = Depends(get_session)) -> SugerirCid:
    return montar_sugerir_cid(session)


def _sugerir_cid_em_segundo_plano(pendencia_id: str) -> None:
    """Roda depois da resposta do POST /eventos, com sessão própria (a da requisição já fechou)."""
    try:
        with Session(engine) as session:
            montar_sugerir_cid(session).executar(pendencia_id)
    except Exception:  # a pendência já existe; sem sugestão, o regulador digita o CID
        logging.getLogger(__name__).exception("Sugestão de CID falhou para %s", pendencia_id)


def get_sugerir_cid_em_segundo_plano() -> Callable[[str], None]:
    return _sugerir_cid_em_segundo_plano


# US-15
def get_registrar_evento(session: Session = Depends(get_session)) -> RegistrarEvento:
    return RegistrarEvento(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           _scorer(session), SqlPendenciaRepository(session),
                           SqlUnidadeDeTrabalho(session))


# US-13/14
def get_decidir(session: Session = Depends(get_session),
                data: date = Depends(get_data_referencia),
                publicar: PublicarFila = Depends(get_publicar_fila)) -> DecidirClasse:
    # Mesma data da fila (US-16): `editado_em` e o envelhecimento do score editado partem dela.
    return DecidirClasse(
        solicitacoes=SqlSolicitacaoRepository(session), eventos=SqlEventoRepository(session),
        decisoes=SqlDecisaoRepository(session), scorer=_scorer(session, data),
        uow=SqlUnidadeDeTrabalho(session), publicar=publicar, fila=SqlFilaRepository(session),
        relogio=lambda: datetime.now(timezone.utc), ref_date=data, notificar=_notificar(session))


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
                       SqlEventoRepository(session), _scorer(session), SqlDecisaoRepository(session))


# US-21
def get_detalhar_solicitacao(session: Session = Depends(get_session),
                              data: date = Depends(get_data_referencia)) -> DetalharSolicitacao:
    # Mesma data da fila publicada: detalhe e fila mostram o mesmo % do prazo (D-70).
    return DetalharSolicitacao(
        solicitacoes=SqlSolicitacaoRepository(session),
        eventos=SqlEventoRepository(session),
        correcoes=SqlCorrecaoRepository(session),
        pendencias=SqlPendenciaRepository(session),
        fila=SqlFilaRepository(session),
        scorer=_scorer(session, data),
        ref_date=data,
        decisoes=SqlDecisaoRepository(session),
    )


# US-18
def criar_classificador_motivo() -> ClassificadorMotivoLLM | None:
    """LLM só com chave e LLM ligado; senão None (os `outro` ficam fora do agrupamento, D-99)."""
    if not (settings.llm_enabled and settings.openrouter_api_key):
        return None
    return ClassificadorMotivoLLM(settings.openrouter_api_key, settings.llm_model,
                                  settings.llm_cache_path.parent / "cache_llm_motivos.json")


def get_gerar_propostas(session: Session = Depends(get_session),
                        data: date = Depends(get_data_referencia)) -> GerarPropostas:
    return GerarPropostas(
        decisoes=SqlDecisaoRepository(session), solicitacoes=SqlSolicitacaoRepository(session),
        propostas=SqlPropostaRepository(session), uow=SqlUnidadeDeTrabalho(session),
        referencia=datetime(data.year, data.month, data.day, tzinfo=timezone.utc),
        classificador=criar_classificador_motivo())


def get_nomes_procedimentos(session: Session = Depends(get_session)) -> dict[str, str]:
    """procedimento_id -> nome, para rotular as propostas. Sem banco, vazio."""
    try:
        solicitacoes = SqlSolicitacaoRepository(session).listar(apenas_ativas=False)
    except SQLAlchemyError:
        session.rollback()
        return {}
    return {s.procedimento_id: s.procedimento for s in solicitacoes if s.procedimento}


# US-19
def get_listar_propostas(session: Session = Depends(get_session),
                         data: date = Depends(get_data_referencia)) -> ListarPropostas:
    return ListarPropostas(SqlPropostaRepository(session), SqlRegraRepository(session),
                           SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           _scorer(session, data), SqlDecisaoRepository(session))


def get_decidir_proposta(session: Session = Depends(get_session),
                         data: date = Depends(get_data_referencia)) -> DecidirProposta:
    return DecidirProposta(SqlPropostaRepository(session), SqlRegraRepository(session),
                           SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           _scorer(session, data), SqlUnidadeDeTrabalho(session),
                           lambda: datetime.now(timezone.utc))


def get_reverter_regra(session: Session = Depends(get_session),
                       data: date = Depends(get_data_referencia)) -> ReverterRegra:
    return ReverterRegra(SqlPropostaRepository(session), SqlRegraRepository(session),
                         SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                         get_scorer(data), SqlUnidadeDeTrabalho(session),
                         lambda: datetime.now(timezone.utc))


# Notificações ao paciente (demo)
def get_enviar_notificacoes(session: Session = Depends(get_session)) -> EnviarNotificacoes:
    return EnviarNotificacoes(SqlNotificacaoRepository(session), criar_notificador(),
                              SqlUnidadeDeTrabalho(session), settings.notifica_destino,
                              settings.notifica_limite_envio)


def get_notificacoes(session: Session = Depends(get_session)) -> SqlNotificacaoRepository:
    return SqlNotificacaoRepository(session)
