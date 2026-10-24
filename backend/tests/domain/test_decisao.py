"""US-13/14: decisão do regulador (regras puras, sem banco)."""
from datetime import date, datetime, timezone

import pytest

from app.domain.decisao import aplicar_decisao, override_removido, validar_decisao, validar_proposta
from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, MotivoCodificado, StatusFila
from app.domain.errors import (
    DecisaoInvalidaError,
    JustificativaObrigatoriaError,
    OncologicoRebaixadoError,
    SemPropostaError,
)
from app.domain.models import Solicitacao

AGORA = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
MOTIVO = MotivoCodificado.PS_RECORRENTE


def _sol(cid="K40.9", prioridade="media", **kw):
    return Solicitacao("SOL-1", "PAC-1", "PROC001", cid, date(2026, 1, 1),
                       prioridade_norm=prioridade, **kw)


@pytest.mark.parametrize("acao", [AcaoDecisao.EDITAR, AcaoDecisao.MANTER])
@pytest.mark.parametrize("motivo,just", [(None, "texto"), (MOTIVO, ""), (MOTIVO, "   ")])
def test_editar_e_manter_exigem_motivo_e_justificativa(acao, motivo, just):
    with pytest.raises(JustificativaObrigatoriaError):
        validar_decisao(_sol(), acao, Classe.B, None, motivo, just)


def test_aprovar_nao_exige_justificativa():
    validar_decisao(_sol(), AcaoDecisao.APROVAR, None, None, None, None)


def test_editar_exige_classe_ou_score():
    with pytest.raises(DecisaoInvalidaError):
        validar_decisao(_sol(), AcaoDecisao.EDITAR, None, None, MOTIVO, "x")


@pytest.mark.parametrize("classe", [Classe.C, Classe.D])
def test_oncologico_nao_pode_ir_para_c_ou_d(classe):
    # SOL-2025-00149: C61
    with pytest.raises(OncologicoRebaixadoError):
        validar_decisao(_sol("C61"), AcaoDecisao.EDITAR, classe, None, MOTIVO, "x")
    validar_decisao(_sol("C61"), AcaoDecisao.EDITAR, Classe.B, None, MOTIVO, "x")  # B pode


def test_aprovar_confirma_a_sugerida_e_desfaz_override():
    s = _sol(classe_medico=Classe.D, score_medico=10.0, editado_manualmente=True)
    assert aplicar_decisao(s, AcaoDecisao.APROVAR, Classe.B, None, None, None, "REG-1", AGORA) is Classe.B
    assert (s.classe_status, s.classe_confirmada, s.classe_medico, s.score_medico) == (
        ClasseStatus.CONFIRMADA, Classe.B, None, None)
    assert s.editado_manualmente is False


def test_editar_grava_override_com_autor():
    s = _sol()
    aplicar_decisao(s, AcaoDecisao.EDITAR, Classe.D, Classe.A2, 150.0, MOTIVO, "REG-1", AGORA)
    assert (s.classe_medico, s.score_medico, s.classe_confirmada) == (Classe.A2, 150.0, Classe.A2)
    assert (s.editado_manualmente, s.editado_por, s.editado_em, s.motivo_codificado) == (
        True, "REG-1", AGORA, MOTIVO)


def test_editar_so_score_mantem_classe_sugerida():
    s = _sol()
    assert aplicar_decisao(s, AcaoDecisao.EDITAR, Classe.C, None, 80.0, MOTIVO, "R", AGORA) is Classe.C
    assert s.score_medico == 80.0


def test_manter_fixa_a_classe_atual_e_recusa_a_sugestao():
    # Nunca confirmado, prioridade "media" -> classe atual implícita C; sugestão A1 recusada.
    s = _sol(prioridade="media")
    assert aplicar_decisao(s, AcaoDecisao.MANTER, Classe.A1, None, None, MOTIVO, "R", AGORA) is Classe.C
    assert s.classe_medico is Classe.C and s.classe_status is ClasseStatus.CONFIRMADA


def test_manter_oncologico_em_d_e_bloqueado_sem_mexer_no_estado():
    # C61 com prioridade "baixa": classe atual implícita D; manter fixaria D -> recusado.
    s = _sol("C61", prioridade="baixa")
    with pytest.raises(OncologicoRebaixadoError):
        aplicar_decisao(s, AcaoDecisao.MANTER, Classe.A2, None, None, MOTIVO, "R", AGORA)
    assert s.classe_medico is None and s.classe_status is ClasseStatus.SUGERIDA_NAO_CONFIRMADA


def test_editar_so_classe_descarta_score_de_outra_classe():
    s = _sol(classe_medico=Classe.C, score_medico=300.0)
    aplicar_decisao(s, AcaoDecisao.EDITAR, Classe.C, Classe.B, None, MOTIVO, "R", AGORA)
    assert s.score_medico is None


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1.0])
def test_score_invalido(score):
    with pytest.raises(DecisaoInvalidaError):
        validar_decisao(_sol(), AcaoDecisao.EDITAR, None, score, MOTIVO, "x")


def test_decisao_descongela_classe_vigente():
    s = _sol(classe_vigente=Classe.C)
    aplicar_decisao(s, AcaoDecisao.APROVAR, Classe.A2, None, None, None, "R", AGORA)
    assert s.classe_vigente is None and s.classe_confirmada is Classe.A2


# --- aprovar só o que o inbox mostraria (D-98) ---

def test_nunca_confirmada_diverge_dois_niveis_tem_proposta():
    validar_proposta(_sol(prioridade="baixa"), Classe.B)  # implícita D, sugerida B: 2 níveis


def test_nunca_confirmada_diverge_so_um_nivel_nao_tem_proposta():
    with pytest.raises(SemPropostaError) as erro:
        validar_proposta(_sol(prioridade="baixa"), Classe.C)  # D -> C: 1 nível

    assert erro.value.codigo == "SEM_PROPOSTA" and erro.value.status_http == 409


def test_confirmada_na_mesma_classe_nao_tem_proposta():
    with pytest.raises(SemPropostaError):
        validar_proposta(_sol(classe_status=ClasseStatus.CONFIRMADA, classe_confirmada=Classe.B), Classe.B)


def test_confirmada_com_classe_diferente_tem_proposta():
    validar_proposta(_sol(classe_status=ClasseStatus.CONFIRMADA, classe_confirmada=Classe.C), Classe.B)


def test_classe_congelada_por_evento_tem_proposta_com_um_nivel():
    validar_proposta(_sol(prioridade="media", classe_vigente=Classe.C), Classe.B)  # US-15 (D-75)


@pytest.mark.parametrize("status", [StatusFila.SUSPENSA, StatusFila.REMOVIDA])
def test_solicitacao_fora_da_fila_nao_tem_proposta(status):
    with pytest.raises(SemPropostaError):
        validar_proposta(_sol(status_fila=status), Classe.A1)


# --- aprovar remove o override e o log diz o que saiu (D-100) ---

def test_aprovar_remove_o_override_inteiro_e_o_texto_do_log_diz_qual_era():
    s = _sol(classe_medico=Classe.C, score_medico=12.5, editado_manualmente=True,
             editado_por="reg-02", editado_em=datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc))

    texto = override_removido(s)
    aplicar_decisao(s, AcaoDecisao.APROVAR, Classe.B, None, None, None, "reg-01", AGORA)

    assert texto == "Override anterior removido (classe C, score 12.5; editado por reg-02 em 12/10/2026)."
    assert (s.classe_medico, s.score_medico, s.editado_manualmente, s.editado_por, s.editado_em) == (
        None, None, False, None, None)


def test_sem_override_o_log_nao_diz_nada():
    assert override_removido(_sol()) is None


def test_aprovar_nao_toca_na_posicao_nem_nos_dados_originais():
    s = _sol(observacoes="x", justificativa_clinica="y")

    aplicar_decisao(s, AcaoDecisao.APROVAR, Classe.A2, None, None, None, "reg-01", AGORA)

    assert (s.observacoes, s.justificativa_clinica, s.prioridade_regulacao) == ("x", "y", None)
    assert s.status_fila == StatusFila.ATIVA
