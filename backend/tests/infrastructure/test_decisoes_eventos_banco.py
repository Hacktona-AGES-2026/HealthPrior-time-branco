"""US-13/14/15 · repositórios no Postgres de teste (pula se o banco estiver fora)."""
from datetime import date, datetime, timezone

from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, MotivoCodificado
from app.domain.models import Decisao, Evento, Pendencia
from app.infrastructure.repositories import (
    SqlDecisaoRepository,
    SqlEventoRepository,
    SqlPendenciaRepository,
    SqlSolicitacaoRepository,
)
from app.infrastructure.tables import SolicitacaoTable

AGORA = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)


def _criar(session):
    session.add(SolicitacaoTable(solicitacao_id="SOL-T1", paciente_id="PAC-T1", nome_paciente="X",
                                 procedimento_id="PROC001", cid_principal="K40.9",
                                 justificativa_clinica="orig", data_entrada_fila=date(2026, 1, 1)))
    session.flush()


def test_salvar_grava_so_o_estado_da_decisao(session):
    _criar(session)
    repo = SqlSolicitacaoRepository(session)
    s = repo.obter("SOL-T1")
    s.classe_status, s.classe_confirmada, s.classe_medico = ClasseStatus.CONFIRMADA, Classe.B, Classe.B
    s.score_medico, s.editado_manualmente, s.editado_por, s.editado_em = 90.0, True, "REG-1", AGORA
    s.motivo_codificado = MotivoCodificado.PS_RECORRENTE
    s.classe_vigente = Classe.C
    s.justificativa_clinica = "não deve ser gravado"
    repo.salvar(s)
    session.expire_all()
    lido = repo.obter("SOL-T1")
    assert (lido.classe_status, lido.classe_confirmada, lido.classe_medico, lido.score_medico) == (
        ClasseStatus.CONFIRMADA, Classe.B, Classe.B, 90.0)
    assert (lido.editado_por, lido.motivo_codificado) == ("REG-1", MotivoCodificado.PS_RECORRENTE)
    assert lido.classe_vigente is Classe.C
    assert lido.justificativa_clinica == "orig"  # original intocado (I-10)


def test_decisao_e_evento_e_pendencia(session):
    _criar(session)
    SqlDecisaoRepository(session).adicionar(Decisao(
        "DEC-1", "SOL-T1", "REG-1", AcaoDecisao.EDITAR, AGORA, Classe.D, Classe.B, 90.0,
        MotivoCodificado.OUTRO, "texto", "swalis-regras-2"))
    [d] = SqlDecisaoRepository(session).listar_por_solicitacao("SOL-T1")
    assert (d.acao, d.classe_sugerida, d.classe_decidida, d.motivo_codificado) == (
        AcaoDecisao.EDITAR, Classe.D, Classe.B, MotivoCodificado.OUTRO)

    SqlEventoRepository(session).adicionar(Evento("EVT-N1", "SOL-T1", "PAC-T1", date(2026, 10, 20),
                                                  "pronto_socorro", "observacao", None, "dor"))
    [e] = SqlEventoRepository(session).listar_por_solicitacao("SOL-T1")
    assert (e.evento_id, e.tipo_evento, e.historico) == ("EVT-N1", "pronto_socorro", False)

    p = Pendencia("", "SOL-T1", "PRE-23", "Desistiu", True, [], "Ligar", aberta_em=date(2026, 10, 20))
    SqlPendenciaRepository(session).salvar(p)
    assert p.pendencia_id == "PEN-0001"
    assert [x.regra for x in SqlPendenciaRepository(session).listar_por_solicitacao("SOL-T1")] == ["PRE-23"]
