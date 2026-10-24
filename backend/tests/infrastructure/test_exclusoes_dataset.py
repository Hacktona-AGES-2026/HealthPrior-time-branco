"""US-11 · exclusões da fila com o dataset real (precisa do Postgres de teste)."""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from sqlmodel import text

from app import cli
from app.application.gerar_fila import GerarFila
from app.application.listar_exclusoes import ListarExclusoes
from app.application.publicar_fila import PublicarFila
from app.config import settings
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlEventoRepository,
    SqlFilaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.verificador import VerificadorOficial
from tests.infrastructure.test_resolver_pendencia import carregar

DOC = "# Decisões\n\n## Solicitações fora da fila\n\n> rascunho\n\n## Premissas\n\n- dados sintéticos\n"


def publicar(session, tmp_path):
    gerar = GerarFila(SqlSolicitacaoRepository(session), SqlEventoRepository(session), criar_swalis(),
                      ExportadorCsv(), settings.ref_date)
    return PublicarFila(gerar, VerificadorOficial(), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
                        lambda: datetime(2026, 10, 24, tzinfo=timezone.utc), tmp_path).executar()


def exclusoes(session) -> ListarExclusoes:
    return ListarExclusoes(SqlSolicitacaoRepository(session), SqlFilaRepository(session))


def test_so_regras_de_saida_e_os_numeros_do_dataset(session):
    carregar(session)
    r = exclusoes(session).executar()
    # PRE-24 (evento órfão) não tem solicitação: nunca aparece aqui
    assert {g.regra for g in r.grupos} <= {"PRE-20", "PRE-21", "PRE-22", "PRE-23", "PRE-25"}
    assert r.fora == sum(g.quantidade for g in r.grupos) == 41  # as 41 suspensas da carga (US-04)
    assert r.total == 941
    assert r.confere is None  # ainda não há fila publicada


def test_bate_com_o_aviso_de_cobertura_do_verificador(session, tmp_path):
    carregar(session)
    publicacao = publicar(session, tmp_path)
    r = exclusoes(session).executar()
    assert r.publicadas == publicacao.total and r.confere is True
    fora_do_verificador = int(re.search(r"(\d+) solicitações da fila não aparecem", publicacao.saida_verificador).group(1))
    assert fora_do_verificador == r.fora


def test_oncologico_nunca_e_suspenso_pela_regra(session):
    """I-02: nenhuma oncológica está fora da fila antes de uma pessoa confirmar a saída."""
    carregar(session)
    assert all(not g.oncologicas for g in exclusoes(session).executar().grupos)


def test_cli_imprime_e_grava_so_a_secao(session, tmp_path, monkeypatch, capsys):
    carregar(session)
    publicar(session, tmp_path)
    doc = tmp_path / "DECISOES.md"
    doc.write_text(DOC, encoding="utf-8")
    monkeypatch.setattr(cli, "engine", session.get_bind())
    monkeypatch.setattr(cli, "settings", cli.settings.__class__(**{**cli.settings.__dict__, "decisoes_path": doc}))

    cli.cmd_decisoes()
    saida = capsys.readouterr().out
    assert "| Motivo (regra) | Quantidade | Solicitações | Observação |" in saida
    assert "Fora da fila: 41 de 941" in saida and "Cobertura: confere" in saida
    assert doc.read_text(encoding="utf-8") == DOC  # sem --gravar não mexe no arquivo

    cli.cmd_decisoes(gravar=True)
    novo = doc.read_text(encoding="utf-8")
    assert "rascunho" not in novo and "PRE-" in novo and "41 de 941" in novo
    assert novo.startswith("# Decisões\n\n## Solicitações fora da fila") and novo.endswith("## Premissas\n\n- dados sintéticos\n")
    cli.cmd_decisoes(gravar=True)
    assert doc.read_text(encoding="utf-8") == novo  # idempotente


def test_cli_alerta_quando_a_cobertura_nao_bate(session, tmp_path, monkeypatch, capsys):
    carregar(session)
    publicar(session, tmp_path)
    session.exec(text("update solicitacoes set status_fila='suspensa', motivo_status='PRE-23' "
                                             "where solicitacao_id=(select min(solicitacao_id) from solicitacoes where status_fila='ativa')"))
    session.commit()
    monkeypatch.setattr(cli, "engine", session.get_bind())
    with pytest.raises(SystemExit) as e:
        cli.cmd_decisoes()
    assert e.value.code == 1 and "a cobertura não bate" in capsys.readouterr().err
