"""US-13: aprovar a classe sugerida (regras puras, sem banco)."""
from datetime import date, datetime, timezone

import pytest

from app.domain.decisao import aprovar, validar_proposta
from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, StatusFila
from app.domain.errors import SemPropostaError
from app.domain.models import Solicitacao

AGORA = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def solicitacao(**kw):
    base = dict(solicitacao_id="SOL-2023-00060", paciente_id="PAC-1", procedimento_id="PROC004",
                cid_principal="K80.1", data_entrada_fila=date(2023, 10, 1), prioridade_norm="baixa")
    base.update(kw)
    return Solicitacao(**base)


# --- só se aprova o que o inbox mostraria ---

def test_nunca_confirmada_diverge_dois_niveis_tem_proposta():
    validar_proposta(solicitacao(prioridade_norm="baixa"), Classe.B)  # implícita D, sugerida B: 2 níveis


def test_nunca_confirmada_diverge_so_um_nivel_nao_tem_proposta():
    with pytest.raises(SemPropostaError) as erro:
        validar_proposta(solicitacao(prioridade_norm="baixa"), Classe.C)  # D -> C: 1 nível

    assert erro.value.codigo == "SEM_PROPOSTA" and erro.value.status_http == 409


def test_confirmada_na_mesma_classe_nao_tem_proposta():
    s = solicitacao(classe_status=ClasseStatus.CONFIRMADA, classe_confirmada=Classe.B)

    with pytest.raises(SemPropostaError):
        validar_proposta(s, Classe.B)


def test_confirmada_com_classe_diferente_tem_proposta():
    s = solicitacao(classe_status=ClasseStatus.CONFIRMADA, classe_confirmada=Classe.C)

    validar_proposta(s, Classe.B)  # qualquer mudança de classe entra


@pytest.mark.parametrize("status", [StatusFila.SUSPENSA, StatusFila.REMOVIDA])
def test_solicitacao_fora_da_fila_nao_tem_proposta(status):
    with pytest.raises(SemPropostaError):
        validar_proposta(solicitacao(status_fila=status), Classe.A1)


# --- aprovar ---

def test_aprovar_confirma_a_classe_sugerida_e_gera_o_registro():
    s = solicitacao()

    d = aprovar(s, Classe.B, "reg-01", AGORA, "swalis-regras-1", "DEC-0001")

    assert (s.classe_status, s.classe_confirmada) == (ClasseStatus.CONFIRMADA, Classe.B)
    assert (d.decisao_id, d.solicitacao_id, d.regulador_id, d.acao) == ("DEC-0001", "SOL-2023-00060", "reg-01", AcaoDecisao.APROVAR)
    assert (d.classe_sugerida, d.classe_decidida, d.data) == (Classe.B, Classe.B, AGORA)
    assert (d.versao_regras, d.procedimento_id, d.justificativa) == ("swalis-regras-1", "PROC004", None)
    assert d.motivo_codificado is None and d.score_decidido is None


def test_aprovar_nao_toca_na_posicao_nem_nos_dados_originais():
    s = solicitacao(observacoes="x", justificativa_clinica="y")

    aprovar(s, Classe.A2, "reg-01", AGORA, "v", "DEC-0001")

    assert (s.observacoes, s.justificativa_clinica, s.prioridade_regulacao) == ("x", "y", None)
    assert s.status_fila == StatusFila.ATIVA


def test_aprovar_remove_o_override_anterior_e_registra_no_log():
    s = solicitacao(classe_medico=Classe.C, score_medico=12.5, editado_manualmente=True,
                    editado_por="reg-02", editado_em=datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc))

    d = aprovar(s, Classe.B, "reg-01", AGORA, "v", "DEC-0002")

    assert (s.classe_medico, s.score_medico, s.editado_manualmente, s.editado_por, s.editado_em) == (None, None, False, None, None)
    assert d.justificativa == "Override anterior removido (classe C, score 12.5; editado por reg-02 em 12/10/2026)."


def test_sem_override_o_log_nao_diz_nada():
    d = aprovar(solicitacao(), Classe.B, "reg-01", AGORA, "v", "DEC-0003")

    assert d.justificativa is None
