"""SqlProcedimentoRepository.obter no Postgres de teste (pula se o banco estiver fora)."""
from app.infrastructure.repositories import SqlProcedimentoRepository
from app.infrastructure.tables import ProcedimentoTable


def test_obter_converte_uti_e_devolve_none_se_ausente(session):
    session.add(ProcedimentoTable(
        procedimento_id="PROC001", procedimento="Facectomia com implante de lente intraocular",
        especialidade="Oftalmologia", porte="pequeno", risco_cirurgico=1, duracao_media_min=30,
        necessita_uti="nao"))
    session.add(ProcedimentoTable(procedimento_id="PROC-UTI", porte="grande", necessita_uti="sim"))
    session.add(ProcedimentoTable(procedimento_id="PROC-EVENT", porte="medio", necessita_uti="eventual"))
    session.flush()
    repo = SqlProcedimentoRepository(session)
    p = repo.obter("PROC001")
    assert (p.porte, p.risco_cirurgico, p.duracao_media_min, p.necessita_uti) == ("pequeno", 1, 30, "nao")
    assert repo.obter("PROC-UTI").necessita_uti == "sim"
    assert repo.obter("PROC-EVENT").necessita_uti == "eventual"
    assert repo.obter("PROC-NAO-EXISTE") is None
