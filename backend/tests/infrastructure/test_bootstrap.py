"""`cli bootstrap`: primeira subida do deploy (precisa do Postgres de teste)."""
from sqlmodel import func, select

from app import cli
from app.infrastructure.tables import FilaPublicadaTable, PropostaRegraTable, SolicitacaoTable


def test_banco_vazio_carrega_publica_e_semeia_e_o_segundo_run_nao_faz_nada(session, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "engine", session.get_bind())
    monkeypatch.setattr(cli, "settings", cli.settings.__class__(**{**cli.settings.__dict__, "output_dir": tmp_path}))
    monkeypatch.setenv("HP_DEMO_SEED", "true")

    cli.cmd_bootstrap()
    session.expire_all()
    assert session.exec(select(func.count()).select_from(SolicitacaoTable)).one() == 941
    assert session.exec(select(func.count()).select_from(FilaPublicadaTable)).one() == 900  # fila publicada (I-07)
    assert session.exec(select(func.count()).select_from(PropostaRegraTable)).one() >= 2  # propostas da demo
    assert "pronto" in capsys.readouterr().out

    cli.cmd_bootstrap()  # reiniciar o serviço não refaz a carga
    assert "nada a fazer" in capsys.readouterr().out


def test_sem_demo_seed_nao_cria_propostas(session, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "engine", session.get_bind())
    monkeypatch.setattr(cli, "settings", cli.settings.__class__(**{**cli.settings.__dict__, "output_dir": tmp_path}))
    monkeypatch.setenv("HP_DEMO_SEED", "false")
    cli.cmd_bootstrap()
    session.expire_all()
    assert session.exec(select(func.count()).select_from(PropostaRegraTable)).one() == 0
