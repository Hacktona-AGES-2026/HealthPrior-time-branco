"""US-07 · resolver pendências com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlmodel import func, select, text

from app.application.carga_inicial import CargaInicial
from app.application.detectar_bloqueantes import DetectarBloqueantes
from app.application.detectar_inconsistencias import DetectarInconsistencias
from app.application.gerar_fila import GerarFila
from app.application.normalizar import Normalizar
from app.application.publicar_fila import PublicarFila
from app.application.recalcular_flags import RecalcularFlags
from app.application.resolver_pendencia import ResolverPendencia
from app.config import settings
from app.domain.enums import ResolucaoPendencia as R
from app.domain.errors import (
    ObservacaoObrigatoriaError,
    PendenciaJaResolvidaError,
    PendenciaNaoEncontradaError,
    ResolucaoInvalidaError,
)
from app.infrastructure.csv_loader import LeitorDataset
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
from app.infrastructure.swalis_stub import SwalisStub
from app.infrastructure.tables import CorrecaoTable, EventoTable, PendenciaTable, SolicitacaoTable
from app.infrastructure.verificador import VerificadorOficial

AGORA = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


class VerificadorReprova:
    def verificar(self, caminho):
        return False, "reprovado"


def repos(session):
    return (SqlSolicitacaoRepository(session), SqlEventoRepository(session), SqlCorrecaoRepository(session),
            SqlPendenciaRepository(session))


def carregar(session):
    """A carga como o CLI faz (normaliza, flags, alertas e bloqueantes); deixa 56 pendências bloqueantes."""
    sol, ev, cor, pen = repos(session)
    CargaInicial(LeitorDataset(settings.data_dir), SqlCargaRepository(session), Normalizar(sol, cor),
                 SqlUnidadeDeTrabalho(session), RecalcularFlags(sol, ev, cor),
                 DetectarInconsistencias(sol, ev, pen, settings.ref_date),
                 DetectarBloqueantes(sol, ev, pen, settings.ref_date)).executar()


def montar(session, tmp_path, verificador=None) -> ResolverPendencia:
    sol, ev, cor, pen = repos(session)
    gerar = GerarFila(sol, ev, SwalisStub(), ExportadorCsv(), settings.ref_date)
    publicar = PublicarFila(gerar, verificador or VerificadorOficial(), SqlFilaRepository(session),
                            SqlUnidadeDeTrabalho(session), lambda: AGORA, tmp_path)
    return ResolverPendencia(pen, sol, ev, cor, SqlUnidadeDeTrabalho(session), publicar, lambda: AGORA,
                             RecalcularFlags(sol, ev, cor))


@pytest.fixture
def resolver(session, tmp_path):
    carregar(session)
    return montar(session, tmp_path)


def pendencia(session, sol_id, regra) -> PendenciaTable:
    session.expire_all()
    return session.exec(select(PendenciaTable).where(
        PendenciaTable.solicitacao_id == sol_id, PendenciaTable.regra == regra)).one()


def solicitacao(session, sol_id) -> SolicitacaoTable:
    session.expire_all()
    return session.get(SolicitacaoTable, sol_id)


def fila_publicada(session):
    return [l.solicitacao_id for l in SqlFilaRepository(session).obter_publicada()]


# --- confirmar saída ---

def test_confirmar_saida_remove_com_motivo_e_registra_quem_e_quando(session, resolver):
    p = pendencia(session, "SOL-2024-00076", "PRE-23")  # desistência

    r = resolver.executar(p.pendencia_id, R.CONFIRMAR_SAIDA, "adm-01", "Confirmado por telefone: desistiu.")

    assert (r.status_fila.value, r.fila_publicada) == ("removida", True)
    s = solicitacao(session, "SOL-2024-00076")
    assert (s.status_fila, s.motivo_status) == ("removida", "PRE-23")  # a regra é o motivo (D-94)
    p = pendencia(session, "SOL-2024-00076", "PRE-23")
    assert (p.status, p.resolvido_por, p.resolucao) == ("resolvida", "adm-01", "confirmar_saida")
    assert p.observacao == "Confirmado por telefone: desistiu." and p.resolvido_em is not None


def test_confirmar_saida_exige_observacao_e_nao_muda_nada(session, resolver):
    p = pendencia(session, "SOL-2024-00076", "PRE-23")

    with pytest.raises(ObservacaoObrigatoriaError):
        resolver.executar(p.pendencia_id, R.CONFIRMAR_SAIDA, "adm-01", "  ")

    assert pendencia(session, "SOL-2024-00076", "PRE-23").status == "aberta"
    assert solicitacao(session, "SOL-2024-00076").status_fila == "suspensa"


def test_oncologico_so_sai_por_decisao_humana(session, tmp_path):
    # I-02: o sistema nunca suspende oncológico; uma pessoa pode confirmar a saída
    carregar(session)
    session.exec(text("update solicitacoes set observacoes='PCT DESISTIU DO PROCEDIMENTO.' where solicitacao_id='SOL-2023-00010'"))
    session.commit()
    sol, ev, _, pen = repos(session)
    DetectarBloqueantes(sol, ev, pen, settings.ref_date).executar()
    SqlUnidadeDeTrabalho(session).confirmar()
    assert solicitacao(session, "SOL-2023-00010").status_fila == "ativa"  # só alerta + pendência
    resolver = montar(session, tmp_path)

    r = resolver.executar(pendencia(session, "SOL-2023-00010", "PRE-23").pendencia_id,
                          R.CONFIRMAR_SAIDA, "adm-01", "Paciente confirmou a desistência.")

    assert r.status_fila.value == "removida"
    assert "SOL-2023-00010" not in fila_publicada(session)


# --- reativar e descartar ---

def test_reativar_volta_a_solicitacao_para_a_fila(session, resolver):
    p = pendencia(session, "SOL-2024-00076", "PRE-23")

    r = resolver.executar(p.pendencia_id, R.REATIVAR, "adm-01")

    assert (r.status_fila.value, r.fila_publicada) == ("ativa", True)
    s = solicitacao(session, "SOL-2024-00076")
    assert (s.status_fila, s.motivo_status) == ("ativa", None)
    assert pendencia(session, "SOL-2024-00076", "PRE-23").status == "resolvida"
    assert "SOL-2024-00076" in fila_publicada(session)


def test_reativada_por_pessoa_nao_e_suspensa_de_novo_pela_deteccao(session, resolver):
    resolver.executar(pendencia(session, "SOL-2024-00076", "PRE-23").pendencia_id, R.REATIVAR, "adm-01")
    sol, ev, _, pen = repos(session)

    DetectarBloqueantes(sol, ev, pen, settings.ref_date).executar()
    SqlUnidadeDeTrabalho(session).confirmar()

    assert solicitacao(session, "SOL-2024-00076").status_fila == "ativa"
    assert pendencia(session, "SOL-2024-00076", "PRE-23").status == "resolvida"


def test_descartar_termina_como_descartada_e_volta_a_fila(session, resolver):
    p = pendencia(session, "SOL-2026-00305", "PRE-25")  # fontes contraditórias

    r = resolver.executar(p.pendencia_id, R.DESCARTAR, "adm-02", "Falso alarme.")

    assert r.status_fila.value == "ativa"
    p = pendencia(session, "SOL-2026-00305", "PRE-25")
    assert (p.status, p.resolvido_por, p.resolucao) == ("descartada", "adm-02", "descartar")
    assert solicitacao(session, "SOL-2026-00305").status_fila == "ativa"


def test_pendencia_nao_bloqueante_so_registra_o_desfecho(session, resolver):
    p = pendencia(session, "SOL-2025-00053", "PRE-10")  # contato perdido: o paciente já está na fila

    r = resolver.executar(p.pendencia_id, R.DESCARTAR, "adm-01")

    assert r.status_fila.value == "ativa"
    assert pendencia(session, "SOL-2025-00053", "PRE-10").status == "descartada"


def test_com_outra_pendencia_bloqueante_aberta_continua_suspensa(session, resolver):
    sol_id = session.exec(text(
        "select solicitacao_id from pendencias where bloqueante and status='aberta' "
        "and regra in ('PRE-20','PRE-21','PRE-22','PRE-23','PRE-25') "
        "group by solicitacao_id having count(*) > 1 order by solicitacao_id limit 1")).first()[0]
    abertas = session.exec(select(PendenciaTable).where(
        PendenciaTable.solicitacao_id == sol_id, PendenciaTable.status == "aberta",
        PendenciaTable.regra.in_(["PRE-20", "PRE-21", "PRE-22", "PRE-23", "PRE-25"]))
        .order_by(PendenciaTable.regra)).all()

    resolver.executar(abertas[0].pendencia_id, R.REATIVAR, "adm-01")

    s = solicitacao(session, sol_id)
    assert (s.status_fila, s.motivo_status) == ("suspensa", abertas[1].regra)  # a outra ainda bloqueia


# --- fundir ---

def test_fundir_mantem_a_mais_antiga_e_remove_a_mais_nova(session, resolver):
    # PAC-00151: SOL-2025-00290 (19/09/2025) e SOL-2025-00348 (19/10/2025)
    p = pendencia(session, "SOL-2025-00348", "PRE-20")

    r = resolver.executar(p.pendencia_id, R.FUNDIR, "adm-01")

    assert r.status_fila.value == "removida"
    nova, antiga = solicitacao(session, "SOL-2025-00348"), solicitacao(session, "SOL-2025-00290")
    assert (nova.status_fila, nova.motivo_status) == ("removida", "PRE-20")
    assert (antiga.status_fila, str(antiga.data_entrada_fila)) == ("ativa", "2025-09-19")
    p = pendencia(session, "SOL-2025-00348", "PRE-20")
    assert (p.status, p.observacao) == ("resolvida", "Fundida com SOL-2025-00290")
    assert fila_publicada(session).count("SOL-2025-00290") == 1 and "SOL-2025-00348" not in fila_publicada(session)


def par_duplicado_com_eventos(session):
    """Um par PRE-20 em que a solicitação mais antiga tem eventos (18 dos 22 pares)."""
    for p in SqlPendenciaRepository(session).listar(regra="PRE-20"):
        mais_antiga = p.evidencias[0].ref
        n = session.exec(select(func.count()).select_from(EventoTable).where(EventoTable.solicitacao_id == mais_antiga)).one()
        if n > 0 and p.solicitacao_id != mais_antiga:
            return p, mais_antiga, n
    raise AssertionError("o dataset deveria ter um par com eventos na mais antiga")


def test_fundir_mantendo_a_mais_nova_move_eventos_herda_a_data_e_registra(session, resolver):
    p, antiga_id, n_eventos = par_duplicado_com_eventos(session)
    data_antiga = str(solicitacao(session, antiga_id).data_entrada_fila)

    r = resolver.executar(p.pendencia_id, R.FUNDIR, "adm-01", fundir_com=p.solicitacao_id)

    assert r.status_fila.value == "ativa"  # a da pendência é quem permanece
    assert solicitacao(session, antiga_id).status_fila == "removida"
    nova = solicitacao(session, p.solicitacao_id)
    assert (nova.status_fila, nova.motivo_status, str(nova.data_entrada_fila)) == ("ativa", None, data_antiga)
    eventos = session.exec(select(func.count()).select_from(EventoTable).where(EventoTable.solicitacao_id == p.solicitacao_id)).one()
    assert eventos == n_eventos
    assert session.exec(select(func.count()).select_from(EventoTable).where(EventoTable.solicitacao_id == antiga_id)).one() == 0
    log = session.exec(select(CorrecaoTable).where(CorrecaoTable.regra == "PRE-20",
                                                   CorrecaoTable.solicitacao_id == p.solicitacao_id)).all()
    assert {c.campo for c in log if not c.campo.startswith("evento:")} == {"data_entrada_fila"}
    assert len([c for c in log if c.campo.startswith("evento:")]) == n_eventos
    assert all(c.original == antiga_id and c.novo == p.solicitacao_id for c in log if c.campo.startswith("evento:"))


def test_fundir_nao_apaga_nenhum_evento(session, resolver):
    p, _, _ = par_duplicado_com_eventos(session)
    total = session.exec(select(func.count()).select_from(EventoTable)).one()

    resolver.executar(p.pendencia_id, R.FUNDIR, "adm-01", fundir_com=p.solicitacao_id)

    assert session.exec(select(func.count()).select_from(EventoTable)).one() == total == 1505


def test_fundir_com_solicitacao_fora_do_par_e_invalido(session, resolver):
    p = pendencia(session, "SOL-2025-00348", "PRE-20")

    with pytest.raises(ResolucaoInvalidaError, match="fundir_com"):
        resolver.executar(p.pendencia_id, R.FUNDIR, "adm-01", fundir_com="SOL-2023-00010")

    assert pendencia(session, "SOL-2025-00348", "PRE-20").status == "aberta"
    assert solicitacao(session, "SOL-2025-00348").status_fila == "suspensa"


# --- evento órfão, erros ---

def test_descartar_evento_orfao_nao_tem_status_de_fila(session, resolver):
    p = pendencia(session, "SOL-2023-00941", "PRE-24")  # EVT-000287

    r = resolver.executar(p.pendencia_id, R.DESCARTAR, "adm-01", "ID conferido: registro antigo.")

    assert r.status_fila is None and r.fila_publicada is True
    assert pendencia(session, "SOL-2023-00941", "PRE-24").status == "descartada"


def test_regra_que_nao_aceita_a_resolucao(session, resolver):
    p = pendencia(session, "SOL-2023-00941", "PRE-24")

    with pytest.raises(ResolucaoInvalidaError):
        resolver.executar(p.pendencia_id, R.CONFIRMAR_SAIDA, "adm-01", "x")


def test_nao_resolve_duas_vezes(session, resolver):
    p = pendencia(session, "SOL-2024-00076", "PRE-23")
    resolver.executar(p.pendencia_id, R.REATIVAR, "adm-01")

    with pytest.raises(PendenciaJaResolvidaError, match="adm-01"):
        resolver.executar(p.pendencia_id, R.DESCARTAR, "adm-02")

    assert pendencia(session, "SOL-2024-00076", "PRE-23").resolvido_por == "adm-01"


def test_pendencia_inexistente(session, resolver):
    with pytest.raises(PendenciaNaoEncontradaError):
        resolver.executar("PEN-9999", R.DESCARTAR, "adm-01")


# --- fila: recalculada, e verificador como portão (I-07) ---

def test_a_fila_e_recalculada_depois_da_resolucao(session, resolver):
    resolver.executar(pendencia(session, "SOL-2024-00076", "PRE-23").pendencia_id, R.REATIVAR, "adm-01")
    antes = len(fila_publicada(session))

    resolver.executar(pendencia(session, "SOL-2026-00305", "PRE-25").pendencia_id, R.DESCARTAR, "adm-01")

    assert len(fila_publicada(session)) == antes + 1 == 902  # 900 ativas + as duas devolvidas


def test_verificador_reprova_resolucao_fica_e_a_fila_anterior_continua(session, tmp_path):
    carregar(session)
    montar(session, tmp_path).executar(  # fila publicada inicial
        pendencia(session, "SOL-2024-00076", "PRE-23").pendencia_id, R.REATIVAR, "adm-01")
    anterior = fila_publicada(session)
    resolver = montar(session, tmp_path, VerificadorReprova())

    r = resolver.executar(pendencia(session, "SOL-2026-00305", "PRE-25").pendencia_id, R.DESCARTAR, "adm-01")

    assert r.fila_publicada is False
    assert pendencia(session, "SOL-2026-00305", "PRE-25").status == "descartada"  # a resolução ficou
    assert solicitacao(session, "SOL-2026-00305").status_fila == "ativa"
    assert fila_publicada(session) == anterior  # I-07: a fila anterior segue valendo


def test_falha_ao_publicar_nao_desfaz_a_resolucao(session, resolver, monkeypatch):
    def quebra():
        raise OSError("disco cheio")

    monkeypatch.setattr(resolver._publicar, "executar", quebra)

    r = resolver.executar(pendencia(session, "SOL-2024-00076", "PRE-23").pendencia_id, R.REATIVAR, "adm-01")

    assert r.fila_publicada is False
    assert pendencia(session, "SOL-2024-00076", "PRE-23").status == "resolvida"


def test_nada_e_apagado(session, resolver):
    for sol_id, regra, resolucao in [("SOL-2024-00076", "PRE-23", R.CONFIRMAR_SAIDA), ("SOL-2025-00348", "PRE-20", R.FUNDIR)]:
        resolver.executar(pendencia(session, sol_id, regra).pendencia_id, resolucao, "adm-01", "ok")

    assert session.exec(select(func.count()).select_from(SolicitacaoTable)).one() == 941
    assert session.exec(select(func.count()).select_from(PendenciaTable)).one() == 164
    assert solicitacao(session, "SOL-2024-00076").observacoes == "PCT DESISTIU DO PROCEDIMENTO. SOLICITA RETIRADA DA FILA."
